"""Phase 6: FastAPI translation endpoint."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.localization_engine import Translator
from backend.localization_engine.languages import DEFAULT_MODEL_NAME, validate_target_lang


app = FastAPI(title="Vocational Content Localization Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASELINE_TRANSLATOR: Translator | None = None
DOMAIN_TRANSLATORS: dict[str, Translator] = {}


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_lang: str = "hin_Deva"
    domain: str = "general"


class TranslateResponse(BaseModel):
    translated_text: str
    target_lang: str
    backend: str
    model_name_or_path: str
    warning: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    backend = BASELINE_TRANSLATOR.backend if BASELINE_TRANSLATOR else "not_loaded"
    return {"status": "ok", "baseline_backend": backend}


@app.post("/translate", response_model=TranslateResponse)
def translate(payload: TranslateRequest) -> TranslateResponse:
    try:
        validate_target_lang(payload.target_lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    translator = select_translator(payload.domain, payload.target_lang)
    try:
        result = translator.translate(payload.text, target_lang=payload.target_lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TranslateResponse(
        translated_text=result.translated_text,
        target_lang=payload.target_lang,
        backend=result.backend,
        model_name_or_path=result.model_name_or_path,
        warning=result.warning,
    )


CURRENT_TRANSLATOR: Translator | None = None
CURRENT_CACHE_KEY: str | None = None


def select_translator(domain: str, target_lang: str) -> Translator:
    global CURRENT_TRANSLATOR, CURRENT_CACHE_KEY

    target_model_path = DEFAULT_MODEL_NAME
    cache_key = f"baseline:{target_lang}"

    if domain == "electrician":
        checkpoint = Path("models") / f"finetuned_{target_lang}"
        if checkpoint.exists():
            target_model_path = str(checkpoint)
            cache_key = f"electrician:{target_lang}"

    # If requested model is already loaded in memory, reuse it
    if CURRENT_TRANSLATOR is not None and CURRENT_CACHE_KEY == cache_key:
        return CURRENT_TRANSLATOR

    # Unload previous model from GPU VRAM to prevent OOM
    if CURRENT_TRANSLATOR is not None:
        try:
            CURRENT_TRANSLATOR.unload()
        except Exception:
            pass

    CURRENT_TRANSLATOR = Translator(target_model_path, force_fallback=force_fallback_enabled())
    CURRENT_CACHE_KEY = cache_key
    return CURRENT_TRANSLATOR


def force_fallback_enabled() -> bool:
    return os.getenv("LOCALIZATION_FORCE_FALLBACK", "").strip().lower() in {"1", "true", "yes"}
