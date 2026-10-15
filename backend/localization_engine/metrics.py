"""Evaluation helpers: BLEU, chrF++, glossary term accuracy, paired bootstrap."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from sacrebleu.metrics import BLEU, CHRF

from .glossary import ELECTRICIAN_GLOSSARIES, TERM_VARIANTS

_BLEU = BLEU()
_CHRF_PP = CHRF(word_order=2)  # chrF++


@dataclass(frozen=True)
class CorpusScores:
    bleu: float
    chrf_pp: float


def score_corpus(predictions: list[str], references: list[str]) -> CorpusScores:
    if not predictions:
        return CorpusScores(0.0, 0.0)
    return CorpusScores(
        bleu=round(_BLEU.corpus_score(predictions, [references]).score, 2),
        chrf_pp=round(_CHRF_PP.corpus_score(predictions, [references]).score, 2),
    )


_NASAL_BEFORE_CONSONANT = re.compile("[ङञणनम]्(?=[क-ह])")


def normalize_indic(text: str) -> str:
    """Orthographic normalisation for term matching only (not for BLEU/chrF).

    Merges spelling variants of the same word: half-nasal + consonant vs anusvara
    (इन्सुलेशन / इंसुलेशन), chandrabindu vs anusvara, nukta, and hyphen vs space.
    """
    text = unicodedata.normalize("NFC", text).replace("़", "").replace("ँ", "ं")
    text = _NASAL_BEFORE_CONSONANT.sub("ं", text)
    text = re.sub(r"[-‐–]", " ", text)
    return re.sub(r"\s+", " ", text)


def term_forms(term: str, target_lang: str) -> list[str]:
    """Accepted (normalised) target renderings of an English glossary term."""
    main = ELECTRICIAN_GLOSSARIES.get(target_lang, {}).get(term)
    if not main:
        return []
    forms = [main, *TERM_VARIANTS.get(target_lang, {}).get(term, ())]
    return [normalize_indic(f) for f in forms]


def term_accuracy(
    predictions: list[str], references: list[str], english_terms: list[list[str]], target_lang: str
) -> tuple[float, int]:
    """Share of glossary terms rendered with an accepted glossary form.

    Only (sentence, term) pairs whose *reference* uses an accepted form are counted,
    so a valid alternative wording in the reference never penalises the system.
    Matching is done on normalised text (see ``normalize_indic``).
    Returns (accuracy, number_of_term_occurrences).
    """
    hits = total = 0
    for prediction, reference, terms in zip(predictions, references, english_terms):
        pred, ref = normalize_indic(prediction), normalize_indic(reference)
        for term in terms:
            forms = term_forms(term, target_lang)
            if not forms or not any(f in ref for f in forms):
                continue
            total += 1
            hits += any(f in pred for f in forms)
    return (round(100 * hits / total, 2) if total else float("nan")), total


def term_compliance(predictions: list[str], english_terms: list[list[str]], target_lang: str) -> tuple[float, int]:
    """Reference-free: share of glossary-term occurrences in the SOURCE that the output renders
    with an accepted glossary form. Measures adherence to the chosen terminology register,
    independent of how the reference was worded. Returns (compliance %, occurrences)."""
    hits = total = 0
    for prediction, terms in zip(predictions, english_terms):
        pred = normalize_indic(prediction)
        for term in terms:
            forms = term_forms(term, target_lang)
            if not forms:
                continue
            total += 1
            hits += any(f in pred for f in forms)
    return (round(100 * hits / total, 2) if total else float("nan")), total


def paired_bootstrap(
    preds_a: list[str], preds_b: list[str], references: list[str], samples: int = 1000, seed: int = 12345
) -> dict[str, float]:
    """Paired bootstrap resampling on chrF++ (Koehn, 2004). Tests whether B beats A.

    Sentence-level chrF++ statistics are extracted once and summed per resample (as in
    sacrebleu's own significance testing), so 1000 resamples take about a second.
    """
    import numpy as np

    refs = [references]
    stats_a = np.array(_CHRF_PP._extract_corpus_statistics(preds_a, refs))
    stats_b = np.array(_CHRF_PP._extract_corpus_statistics(preds_b, refs))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(references), size=(samples, len(references)))
    deltas = np.array(
        [
            _CHRF_PP._compute_score_from_stats(list(stats_b[row].sum(axis=0))).score
            - _CHRF_PP._compute_score_from_stats(list(stats_a[row].sum(axis=0))).score
            for row in idx
        ]
    )
    return {
        "delta_chrf_pp_mean": round(float(deltas.mean()), 2),
        "delta_ci95_low": round(float(np.percentile(deltas, 2.5)), 2),
        "delta_ci95_high": round(float(np.percentile(deltas, 97.5)), 2),
        "p_value": round(float((deltas <= 0).mean()), 4),
    }
