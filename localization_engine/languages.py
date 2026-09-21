"""Language metadata for IndicTrans2 English-to-Indic experiments."""

from __future__ import annotations

from dataclasses import dataclass


SOURCE_LANG = "eng_Latn"
DEFAULT_MODEL_NAME = "ai4bharat/indictrans2-en-indic-dist-200M"


@dataclass(frozen=True)
class Language:
    code: str
    name: str


SCHEDULED_LANGUAGE_TARGETS: tuple[Language, ...] = (
    Language("asm_Beng", "Assamese"),
    Language("ben_Beng", "Bengali"),
    Language("brx_Deva", "Bodo"),
    Language("doi_Deva", "Dogri"),
    Language("guj_Gujr", "Gujarati"),
    Language("hin_Deva", "Hindi"),
    Language("kan_Knda", "Kannada"),
    Language("kas_Arab", "Kashmiri"),
    Language("gom_Deva", "Konkani"),
    Language("mai_Deva", "Maithili"),
    Language("mal_Mlym", "Malayalam"),
    Language("mni_Mtei", "Manipuri"),
    Language("mar_Deva", "Marathi"),
    Language("npi_Deva", "Nepali"),
    Language("ory_Orya", "Odia"),
    Language("pan_Guru", "Punjabi"),
    Language("san_Deva", "Sanskrit"),
    Language("sat_Olck", "Santali"),
    Language("snd_Arab", "Sindhi"),
    Language("tam_Taml", "Tamil"),
    Language("tel_Telu", "Telugu"),
    Language("urd_Arab", "Urdu"),
)

LANGUAGE_NAMES = {lang.code: lang.name for lang in SCHEDULED_LANGUAGE_TARGETS}
SUPPORTED_LANGUAGE_CODES = set(LANGUAGE_NAMES)

# Phase 3/4 scope from the brief.
PRIMARY_DOMAIN_LANGS = ("hin_Deva",)
STRETCH_DOMAIN_LANGS = ("gom_Deva", "mai_Deva", "doi_Deva")


def validate_target_lang(target_lang: str) -> None:
    if target_lang not in SUPPORTED_LANGUAGE_CODES:
        supported = ", ".join(sorted(SUPPORTED_LANGUAGE_CODES))
        raise ValueError(f"Unsupported target language '{target_lang}'. Supported: {supported}")
