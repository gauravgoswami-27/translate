"""Phase 6: FastAPI translation service (local).

Models:
  base    - IndicTrans2 en-indic dist-200M
  raw     - + LoRA adapter distilled on raw teacher drafts   (run 4, models/it2_lora_joint)
  formal  - + LoRA distilled on terminology-repaired, case-fixed drafts (run 6, models/it2_lora_joint_formal_v2)
  formal_run5 - the run-5 adapter (before the case-ending fix), kept for comparison

Routing with model="auto": domain "electrician" + a domain language -> LOCALIZATION_DOMAIN_MODEL
(default "formal"); everything else -> base.

Run from the repository root:
    backend/.venv-api/bin/uvicorn backend.api.main:app --port 8000
Environment variables:
    HF_TOKEN / `hf auth login`   access to the gated IndicTrans2 base model
    LOCALIZATION_DOMAIN_MODEL            formal | raw | base   (default formal)
    LOCALIZATION_PRELOAD                 e.g. "formal,base": load at startup instead of first request
    LOCALIZATION_FORCE_FALLBACK=1        glossary-only fallback, for frontend work without a model
    CORS_ORIGINS                         extra allowed origins, comma-separated (local origins are always allowed)
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
from backend.localization_engine.languages import (
    DEFAULT_MODEL_NAME,
    DOMAIN_LANGS,
    LANGUAGE_NAMES,
    ORIGINAL_DOMAIN_LANGS,
    validate_target_lang,
)
from backend.localization_engine.metrics import normalize_indic, term_forms
from backend.localization_engine.paths import MODELS_DIR
from backend.localization_engine.translator import adapter_languages
from backend.localization_engine.terminology import translate_with_term_fallback

MODEL_PATHS: dict[str, str] = {
    "base": DEFAULT_MODEL_NAME,
    "raw": str(MODELS_DIR / "it2_lora_joint"),
    "formal": str(MODELS_DIR / "it2_lora_joint_formal_v2"),
    "formal_run5": str(MODELS_DIR / "it2_lora_joint_formal"),
    "formal9": str(MODELS_DIR / "it2_lora_joint9_formal"),  # run 7: 9 languages (used once installed)
}
DOMAIN_MODEL: str = os.getenv("LOCALIZATION_DOMAIN_MODEL", "formal")
FORCE_FALLBACK = os.getenv("LOCALIZATION_FORCE_FALLBACK", "").strip().lower() in {"1", "true", "yes"}


def model_available(key: str) -> bool:
    return key == "base" or os.path.exists(os.path.join(MODEL_PATHS[key], "adapter_config.json"))


def model_languages(key: str) -> list[str]:
    """Languages a model is trained for (all 22 for the base model)."""
    if key == "base":
        return list(LANGUAGE_NAMES)
    return adapter_languages(MODEL_PATHS[key]) or list(ORIGINAL_DOMAIN_LANGS)


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
    # Any local dev origin (localhost / 127.0.0.1, any port, e.g. Vite on 5173 or 5174),
    # plus extra origins from CORS_ORIGINS (comma-separated) for a deployed frontend.
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?",
    allow_origins=[o for o in os.getenv("CORS_ORIGINS", "").split(",") if o],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------------------- schemas

class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    target_lang: str = "hin_Deva"
    domain: Literal["general", "electrician"] = "general"
    model: Literal["auto", "base", "raw", "formal", "formal_run5", "formal9"] = "auto"
    terminology: Literal["hybrid", "none", "placeholder"] = Field(
        "hybrid",
        description='"hybrid": normal translation, re-translated with placeholders only if a glossary term is missing; '
        '"placeholder": always force glossary terms (less fluent); "none": model output as is',
    )


class BatchTranslateRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=64)
    target_lang: str = "hin_Deva"
    domain: Literal["general", "electrician"] = "general"
    model: Literal["auto", "base", "raw", "formal", "formal_run5", "formal9"] = "auto"
    terminology: Literal["hybrid", "none", "placeholder"] = "hybrid"


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
    placeholder_retry: bool = False
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
        trained = model_languages(requested)
        if requested != "base" and target_lang not in trained:
            warning = f"The '{requested}' adapter was trained only on {', '.join(trained)}; output for {target_lang} is unvalidated."
        return requested, warning
    if domain == "electrician":
        # First installed model in the preference order that was trained on this language.
        for key in dict.fromkeys((DOMAIN_MODEL, "formal9", "formal", "raw")):
            if key in MODEL_PATHS and model_available(key) and target_lang in model_languages(key):
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
    glossary = ELECTRICIAN_GLOSSARIES.get(target_lang, {})
    terms = [[t for t in find_glossary_terms(text) if t in glossary] for text in texts]
    # Terminology enforcement is for electrician content in languages that have a glossary.
    if domain != "electrician" or not glossary:
        terminology = "none"

    start = time.time()
    retried = [False] * len(texts)
    with lock:
        if terminology == "hybrid":
            outputs, retried = translate_with_term_fallback(translator, texts, target_lang, terms)
        elif terminology == "placeholder":
            outputs = translator.translate_batch(
                texts, target_lang, term_placeholders=[[(t, glossary[t]) for t in ts] for ts in terms]
            )
            retried = [bool(ts) for ts in terms]
        else:
            outputs = translator.translate_batch(texts, target_lang)
    latency = int(1000 * (time.time() - start))
    return [
        TranslateResponse(
            translated_text=out,
            target_lang=target_lang,
            model=key,
            model_name_or_path=translator.model_name_or_path,
            backend=translator.backend,
            terminology=terminology,
            placeholder_retry=retry,
            glossary_terms=glossary_report(src, out, target_lang),
            latency_ms=latency,
            warning=warning or translator.warning,
        )
        for src, out, retry in zip(texts, outputs, retried)
    ]


# ----------------------------------------------------------------------------- routes

@app.get("/health")
def health() -> dict[str, object]:
    import torch

    return {
        "status": "ok",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "models_available": {k: model_available(k) for k in MODEL_PATHS},
        "model_languages": {k: model_languages(k) for k in MODEL_PATHS if k != "base" and model_available(k)},
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
