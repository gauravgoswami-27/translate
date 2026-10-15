"""Small transparent glossary used for offline smoke tests and term extraction."""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

from .paths import DATA_DIR


# The glossary lives in data/glossary/electrician_glossary.csv so language experts can edit
# it in a spreadsheet. Two registers per language:
#   formal   - native/standard technical terms (active; project decision 2026-10-15)
#   loanword - the v1 hand-written English-loanword glossary, kept for comparison
# Status of formal entries: standard (NCERT/CSTT usage), proposed (needs expert check),
# loanword_kept (no established native term in use, e.g. मेगर).
# Variants are alternative spellings/forms of the SAME term. Wrong-sense renderings such as
# चरण ("stage") for "phase" or पृथ्वी ("planet") for "earthing" must never be listed.
GLOSSARY_FILE = DATA_DIR / "glossary" / "electrician_glossary.csv"
ACTIVE_REGISTER = os.getenv("LE_TERM_REGISTER", "formal")


def load_glossary(register: str = ACTIVE_REGISTER, path: Path = GLOSSARY_FILE):
    """Returns ({lang: {english: primary}}, {lang: {english: (variants...)}}, {lang: {english: status}})."""
    primary: dict[str, dict[str, str]] = {}
    variants: dict[str, dict[str, tuple[str, ...]]] = {}
    status: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["register"] != register:
                continue
            lang, term = row["target_lang"], row["english_term"]
            primary.setdefault(lang, {})[term] = row["term"]
            variants.setdefault(lang, {})[term] = tuple(v for v in row["variants"].split("|") if v)
            status.setdefault(lang, {})[term] = row["status"]
    if not primary:
        raise ValueError(f"No '{register}' entries in {path}")
    return primary, variants, status


ELECTRICIAN_GLOSSARIES, TERM_VARIANTS, TERM_STATUS = load_glossary()


# English-only electrician vocabulary used to find terminology-rich sentences
# (test-set stratification). Term scoring only uses the glossary file above, because it
# needs a target term per language.
EXTRA_DOMAIN_TERMS: tuple[str, ...] = (
    "alternator", "armature", "battery", "bus bar", "busbar", "capacitance", "commutator",
    "conductor", "contactor", "continuity", "current transformer", "distribution board",
    "earth electrode", "earth resistance", "earth tester", "energy meter", "field winding",
    "frequency", "galvanometer", "generator", "inductance", "induction motor", "insulation resistance",
    "insulator", "kilowatt", "lamp", "megohm", "miniature circuit breaker", "multimeter", "ohm",
    "overload relay", "potential difference", "power factor", "rectifier", "relay", "rheostat",
    "rotor", "short circuit", "solder", "soldering iron", "starter", "stator", "step-down",
    "transformer", "transistor", "diode", "wattmeter", "wiring", "watt", "volt", "ampere",
    "test lamp", "neon tester", "plier", "screw driver", "elcb", "rccb", "mcb", "ups", "inverter",
)


_SOURCE_TERM_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in sorted(next(iter(ELECTRICIAN_GLOSSARIES.values())), key=len, reverse=True)) + r")s?\b",
    re.IGNORECASE,
)


def find_glossary_terms(english_text: str) -> list[str]:
    """English glossary terms occurring in a source sentence (same matching as build_corpus)."""
    return sorted({m.group(1).lower() for m in _SOURCE_TERM_RE.finditer(english_text)})


def constraint_forms(term: str, target_lang: str) -> list[str]:
    """Surface forms the decoder may be forced to produce for a term: the glossary term and its
    variants, each as written and in normalised spelling (deduplicated, order kept)."""
    from .metrics import normalize_indic  # local import: metrics imports this module

    main = ELECTRICIAN_GLOSSARIES.get(target_lang, {}).get(term)
    if not main:
        return []
    forms: list[str] = []
    for form in (main, *TERM_VARIANTS.get(target_lang, {}).get(term, ())):
        for candidate in (form, normalize_indic(form)):
            if candidate not in forms:
                forms.append(candidate)
    return forms


def glossary_translate(text: str, target_lang: str) -> str:
    """Return a deterministic glossary-substitution translation hint."""
    glossary = ELECTRICIAN_GLOSSARIES.get(target_lang, ELECTRICIAN_GLOSSARIES["hin_Deva"])
    translated = text
    for english, target in sorted(glossary.items(), key=lambda item: len(item[0]), reverse=True):
        translated = re.sub(rf"\b{re.escape(english)}\b", target, translated, flags=re.IGNORECASE)
    return f"[fallback:{target_lang}] {translated}"
