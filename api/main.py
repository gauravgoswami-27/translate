"""Phase 6: FastAPI translation endpoint."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from localization_engine import Translator
from localization_engine.languages import DEFAULT_MODEL_NAME, validate_target_lang


app = FastAPI(title="Vocational Content Localization Engine", version="0.1.0")

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


def select_translator(domain: str, target_lang: str) -> Translator:
    global BASELINE_TRANSLATOR
    if BASELINE_TRANSLATOR is None:
        BASELINE_TRANSLATOR = Translator(DEFAULT_MODEL_NAME, force_fallback=force_fallback_enabled())

    if domain != "electrician":
        return BASELINE_TRANSLATOR

    checkpoint = Path("models") / f"finetuned_{target_lang}"
    if not checkpoint.exists():
        return BASELINE_TRANSLATOR

    cache_key = f"{domain}:{target_lang}"
    if cache_key not in DOMAIN_TRANSLATORS:
        DOMAIN_TRANSLATORS[cache_key] = Translator(str(checkpoint), force_fallback=force_fallback_enabled())
    return DOMAIN_TRANSLATORS[cache_key]


def force_fallback_enabled() -> bool:
    return os.getenv("LOCALIZATION_FORCE_FALLBACK", "").strip().lower() in {"1", "true", "yes"}
