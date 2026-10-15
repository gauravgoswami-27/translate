"""Phase 6: FastAPI translation endpoint.

``domain == "electrician"`` + a domain language routes to the LoRA-adapted model
(models/it2_lora_joint); everything else uses the base IndicTrans2 model.
Both 200M models are small, so they are cached side by side.
"""

from __future__ import annotations

import os
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.localization_engine import Translator
from backend.localization_engine.languages import DEFAULT_MODEL_NAME, DOMAIN_LANGS, validate_target_lang
from backend.localization_engine.paths import MODELS_DIR

DOMAIN_ADAPTER = MODELS_DIR / os.getenv("LOCALIZATION_ADAPTER", "it2_lora_joint")

app = FastAPI(title="Vocational Content Localization Engine", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    target_lang: str = "hin_Deva"
    domain: str = "general"


class TranslateResponse(BaseModel):
    translated_text: str
    target_lang: str
    backend: str
    model_name_or_path: str
    warning: str | None = None


@lru_cache(maxsize=2)
def get_translator(model_name_or_path: str) -> Translator:
    force = os.getenv("LOCALIZATION_FORCE_FALLBACK", "").strip().lower() in {"1", "true", "yes"}
    return Translator(model_name_or_path, force_fallback=force)


def select_model(domain: str, target_lang: str) -> str:
    if domain == "electrician" and target_lang in DOMAIN_LANGS and (DOMAIN_ADAPTER / "adapter_config.json").exists():
        return str(DOMAIN_ADAPTER)
    return DEFAULT_MODEL_NAME


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "base_model": DEFAULT_MODEL_NAME,
        "domain_adapter_available": (DOMAIN_ADAPTER / "adapter_config.json").exists(),
        "domain_langs": list(DOMAIN_LANGS),
    }


@app.post("/translate", response_model=TranslateResponse)
def translate(payload: TranslateRequest) -> TranslateResponse:
    try:
        validate_target_lang(payload.target_lang)
        translator = get_translator(select_model(payload.domain, payload.target_lang))
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
