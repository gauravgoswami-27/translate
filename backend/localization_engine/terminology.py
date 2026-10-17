"""Terminology helpers shared by the API and the evaluation.

Hybrid enforcement: translate normally; only for sentences whose output misses a glossary
term, translate again with entity placeholders for the missing terms, and keep the retry
if it now contains them. Run 5 showed placeholders cost fluency (-4 to -6 chrF++) when
applied to every sentence; with a terminology-aware model only a few sentences (rare
terms such as "live wire") need the retry, so the cost is paid only there.
"""

from __future__ import annotations

from .glossary import ELECTRICIAN_GLOSSARIES, TERM_VARIANTS
from .metrics import normalize_indic, term_forms
from .translator import attach_case_suffixes


def missing_terms(translation: str, english_terms: list[str], target_lang: str) -> list[str]:
    normalized = normalize_indic(translation)
    return [t for t in english_terms if term_forms(t, target_lang) and not any(f in normalized for f in term_forms(t, target_lang))]


def translate_with_term_fallback(translator, texts: list[str], target_lang: str, english_terms: list[list[str]], **kwargs):
    """Returns (translations, retried flags). Also re-attaches case endings that the run-5
    model learned to write detached after glossary terms (Maithili/Konkani)."""
    outputs = translator.translate_batch(texts, target_lang, **kwargs)
    glossary = ELECTRICIAN_GLOSSARIES.get(target_lang, {})
    todo = [(i, missing_terms(out, terms, target_lang)) for i, (out, terms) in enumerate(zip(outputs, english_terms))]
    todo = [(i, miss) for i, miss in todo if miss]
    retried = [False] * len(texts)
    if todo:
        retries = translator.translate_batch(
            [texts[i] for i, _ in todo],
            target_lang,
            term_placeholders=[[(t, glossary[t]) for t in miss if t in glossary] for _, miss in todo],
            **kwargs,
        )
        for (i, miss), retry in zip(todo, retries):
            if len(missing_terms(retry, miss, target_lang)) < len(miss):
                outputs[i], retried[i] = retry, True
    forms = list(glossary.values()) + [v for vs in TERM_VARIANTS.get(target_lang, {}).values() for v in vs]
    return [attach_case_suffixes(out, forms, target_lang) for out in outputs], retried
