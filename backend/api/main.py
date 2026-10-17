"""Phase 6: FastAPI translation service (local).

Models:
  base    - IndicTrans2 en-indic dist-200M
  raw     - + LoRA adapter distilled on raw teacher drafts   (run 4, models/it2_lora_joint)
  formal  - + LoRA adapter distilled on terminology-repaired drafts (run 5, models/it2_lora_joint_formal)

Routing with model="auto": domain "electrician" + a domain language -> LOCALIZATION_DOMAIN_MODEL
(default "formal"); everything else -> base.

Run from the repository root:
    backend/.venv-api/bin/uvicorn backend.api.main:app --port 8000
Environment variables:
    HF_TOKEN / `hf auth login`   access to the gated IndicTrans2 base model
    LOCALIZATION_DOMAIN_MODEL            formal | raw | base   (default formal)
    LOCALIZATION_PRELOAD                 e.g. "formal,base": load at startup instead of first request
    LOCALIZATION_FORCE_FALLBACK=1        glossary-only fallback, for frontend work without a model
    CORS_ORIGINS                         comma-separated (default http://localhost:5173)
"""

from __future__ import annotations

import os
import threading
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.localization_engine import Translator
from backend.localization_engine.glossary import (
    ACTIVE_REGISTER,
    ELECTRICIAN_GLOSSARIES,
    TERM_STATUS,
    TERM_VARIANTS,
    find_glossary_terms,
)
from backend.localization_engine.languages import DEFAULT_MODEL_NAME, DOMAIN_LANGS, LANGUAGE_NAMES, validate_target_lang
from backend.localization_engine.metrics import normalize_indic, term_forms
from backend.localization_engine.paths import MODELS_DIR

ModelKey = Literal["base", "raw", "formal"]
MODEL_PATHS: dict[str, str] = {
    "base": DEFAULT_MODEL_NAME,
    "raw": str(MODELS_DIR / "it2_lora_joint"),
    "formal": str(MODELS_DIR / "it2_lora_joint_formal"),
}
DOMAIN_MODEL: str = os.getenv("LOCALIZATION_DOMAIN_MODEL", "formal")
FORCE_FALLBACK = os.getenv("LOCALIZATION_FORCE_FALLBACK", "").strip().lower() in {"1", "true", "yes"}


def model_available(key: str) -> bool:
    return key == "base" or os.path.exists(os.path.join(MODEL_PATHS[key], "adapter_config.json"))


class ModelPool:
    """Loads each model once. IndicTrans2's processor keeps per-batch state, so every
    model also gets a lock: concurrent requests on the same model run one at a time."""

    def __init__(self) -> None:
        self._models: dict[str, tuple[Translator, threading.Lock]] = {}
        self._loading = threading.Lock()

    def get(self, key: str) -> tuple[Translator, threading.Lock]:
        with self._loading:
            if key not in self._models:
                start = time.time()
                translator = Translator(MODEL_PATHS[key], force_fallback=FORCE_FALLBACK)
                print(f"Loaded model '{key}' ({translator.backend}) in {time.time() - start:.1f}s")
                self._models[key] = (translator, threading.Lock())
            return self._models[key]

    def loaded(self) -> dict[str, str]:
        return {key: t.backend for key, (t, _) in self._models.items()}


POOL = ModelPool()


@asynccontextmanager
async def lifespan(_: FastAPI):
    for key in filter(None, os.getenv("LOCALIZATION_PRELOAD", "").split(",")):
        if key in MODEL_PATHS and model_available(key):
            POOL.get(key)
    yield


app = FastAPI(title="Vocational Content Localization Engine", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------------------- schemas

class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    target_lang: str = "hin_Deva"
    domain: Literal["general", "electrician"] = "general"
    model: Literal["auto", "base", "raw", "formal"] = "auto"
    terminology: Literal["none", "placeholder"] = Field(
        "none", description='"placeholder" forces glossary terms via entity placeholders (works with any model, less fluent)'
    )


class BatchTranslateRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=64)
    target_lang: str = "hin_Deva"
    domain: Literal["general", "electrician"] = "general"
    model: Literal["auto", "base", "raw", "formal"] = "auto"
    terminology: Literal["none", "placeholder"] = "none"


class GlossaryHit(BaseModel):
    english: str
    glossary_term: str
    used: bool


class TranslateResponse(BaseModel):
    translated_text: str
    target_lang: str
    model: str
    model_name_or_path: str
    backend: str
    terminology: str
    glossary_terms: list[GlossaryHit]
    latency_ms: int
    warning: str | None = None


class BatchTranslateResponse(BaseModel):
    results: list[TranslateResponse]
    latency_ms: int


# ----------------------------------------------------------------------------- logic

def select_model(requested: str, domain: str, target_lang: str) -> tuple[str, str | None]:
    """Returns (model key, warning)."""
    if requested != "auto":
        if not model_available(requested):
            raise HTTPException(status_code=400, detail=f"Model '{requested}' is not installed (missing adapter).")
        warning = None
        if requested != "base" and target_lang not in DOMAIN_LANGS:
            warning = f"The '{requested}' adapter was trained only on {', '.join(DOMAIN_LANGS)}; output for {target_lang} is unvalidated."
        return requested, warning
    if domain == "electrician" and target_lang in DOMAIN_LANGS:
        for key in (DOMAIN_MODEL, "formal", "raw"):
            if key in MODEL_PATHS and model_available(key):
                return key, None
    return "base", None


def glossary_report(source: str, translation: str, target_lang: str) -> list[GlossaryHit]:
    glossary = ELECTRICIAN_GLOSSARIES.get(target_lang, {})
    normalized = normalize_indic(translation)
    return [
        GlossaryHit(english=t, glossary_term=glossary[t], used=any(f in normalized for f in term_forms(t, target_lang)))
        for t in find_glossary_terms(source)
        if t in glossary
    ]


def run_translation(texts: list[str], target_lang: str, domain: str, model: str, terminology: str) -> list[TranslateResponse]:
    try:
        validate_target_lang(target_lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    texts = [t.strip() for t in texts]
    if not all(texts):
        raise HTTPException(status_code=400, detail="Input text must not be empty.")

    key, warning = select_model(model, domain, target_lang)
    translator, lock = POOL.get(key)
    kwargs = {}
    if terminology == "placeholder":
        glossary = ELECTRICIAN_GLOSSARIES.get(target_lang, {})
        kwargs["term_placeholders"] = [[(t, glossary[t]) for t in find_glossary_terms(text) if t in glossary] for text in texts]

    start = time.time()
    with lock:
        outputs = translator.translate_batch(texts, target_lang, **kwargs)
    latency = int(1000 * (time.time() - start))
    return [
        TranslateResponse(
            translated_text=out,
            target_lang=target_lang,
            model=key,
            model_name_or_path=translator.model_name_or_path,
            backend=translator.backend,
            terminology=terminology,
            glossary_terms=glossary_report(src, out, target_lang),
            latency_ms=latency,
            warning=warning or translator.warning,
        )
        for src, out in zip(texts, outputs)
    ]


# ----------------------------------------------------------------------------- routes

@app.get("/health")
def health() -> dict[str, object]:
    import torch

    return {
        "status": "ok",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "models_available": {k: model_available(k) for k in MODEL_PATHS},
        "models_loaded": POOL.loaded(),
        "domain_model": DOMAIN_MODEL,
        "domain_langs": list(DOMAIN_LANGS),
        "term_register": ACTIVE_REGISTER,
        "fallback_mode": FORCE_FALLBACK,
    }


@app.get("/languages")
def languages() -> dict[str, object]:
    return {"languages": LANGUAGE_NAMES, "domain_langs": list(DOMAIN_LANGS)}


@app.get("/glossary/{target_lang}")
def glossary(target_lang: str) -> dict[str, object]:
    if target_lang not in ELECTRICIAN_GLOSSARIES:
        raise HTTPException(status_code=404, detail=f"No glossary for {target_lang}; available: {sorted(ELECTRICIAN_GLOSSARIES)}")
    return {
        "target_lang": target_lang,
        "register": ACTIVE_REGISTER,
        "terms": [
            {"english": t, "term": term, "variants": list(TERM_VARIANTS[target_lang].get(t, ())), "status": TERM_STATUS[target_lang][t]}
            for t, term in sorted(ELECTRICIAN_GLOSSARIES[target_lang].items())
        ],
    }


@app.post("/translate", response_model=TranslateResponse)
def translate(payload: TranslateRequest) -> TranslateResponse:
    return run_translation([payload.text], payload.target_lang, payload.domain, payload.model, payload.terminology)[0]


@app.post("/translate/batch", response_model=BatchTranslateResponse)
def translate_batch(payload: BatchTranslateRequest) -> BatchTranslateResponse:
    start = time.time()
    results = run_translation(payload.texts, payload.target_lang, payload.domain, payload.model, payload.terminology)
    return BatchTranslateResponse(results=results, latency_ms=int(1000 * (time.time() - start)))
