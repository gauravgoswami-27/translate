"""Language metadata and model identifiers for IndicTrans2 English-to-Indic experiments."""

from __future__ import annotations

from dataclasses import dataclass


SOURCE_LANG = "eng_Latn"

# Student model that is fine-tuned (fits a Kaggle T4/P100 comfortably).
DEFAULT_MODEL_NAME = "ai4bharat/indictrans2-en-indic-dist-200M"
# Teacher model used to draft synthetic training references and as an upper-bound baseline.
TEACHER_MODEL_NAME = "ai4bharat/indictrans2-en-indic-1B"


@dataclass(frozen=True)
class Language:
    code: str
    name: str
    short: str  # suffix used in corpus/model file names


# All 22 scheduled languages, using the scripts of the IN22 benchmark (all supported by IndicTrans2).
SCHEDULED_LANGUAGE_TARGETS: tuple[Language, ...] = (
    Language("asm_Beng", "Assamese", "as"),
    Language("ben_Beng", "Bengali", "bn"),
    Language("brx_Deva", "Bodo", "brx"),
    Language("doi_Deva", "Dogri", "doi"),
    Language("guj_Gujr", "Gujarati", "gu"),
    Language("hin_Deva", "Hindi", "hi"),
    Language("kan_Knda", "Kannada", "kn"),
    Language("kas_Arab", "Kashmiri", "ks"),
    Language("gom_Deva", "Konkani", "gom"),
    Language("mai_Deva", "Maithili", "mai"),
    Language("mal_Mlym", "Malayalam", "ml"),
    Language("mni_Mtei", "Manipuri", "mni"),
    Language("mar_Deva", "Marathi", "mr"),
    Language("npi_Deva", "Nepali", "ne"),
    Language("ory_Orya", "Odia", "or"),
    Language("pan_Guru", "Punjabi", "pa"),
    Language("san_Deva", "Sanskrit", "sa"),
    Language("sat_Olck", "Santali", "sat"),
    Language("snd_Deva", "Sindhi", "sd"),
    Language("tam_Taml", "Tamil", "ta"),
    Language("tel_Telu", "Telugu", "te"),
    Language("urd_Arab", "Urdu", "ur"),
)

LANGUAGE_NAMES = {lang.code: lang.name for lang in SCHEDULED_LANGUAGE_TARGETS}
LANG_SHORT = {lang.code: lang.short for lang in SCHEDULED_LANGUAGE_TARGETS}
SUPPORTED_LANGUAGE_CODES = set(LANGUAGE_NAMES)

# Domain fine-tuning scope.
PRIMARY_DOMAIN_LANGS = ("hin_Deva",)
STRETCH_DOMAIN_LANGS = ("gom_Deva", "mai_Deva", "doi_Deva")
ORIGINAL_DOMAIN_LANGS = PRIMARY_DOMAIN_LANGS + STRETCH_DOMAIN_LANGS  # runs 4-6
EXTENDED_DOMAIN_LANGS = ("mar_Deva", "guj_Gujr", "tam_Taml", "tel_Telu", "kan_Knda")  # added in run 7
DOMAIN_LANGS = ORIGINAL_DOMAIN_LANGS + EXTENDED_DOMAIN_LANGS


def validate_target_lang(target_lang: str) -> None:
    if target_lang not in SUPPORTED_LANGUAGE_CODES:
        supported = ", ".join(sorted(SUPPORTED_LANGUAGE_CODES))
        raise ValueError(f"Unsupported target language '{target_lang}'. Supported: {supported}")
