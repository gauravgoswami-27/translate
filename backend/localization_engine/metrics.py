"""Evaluation helpers for BLEU, chrF, and domain term matching."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CorpusScores:
    bleu: float
    chrf: float
    metric_backend: str


def score_corpus(predictions: list[str], references: list[str]) -> CorpusScores:
    if not predictions:
        return CorpusScores(0.0, 0.0, "empty")

    try:
        import sacrebleu
    except Exception:
        return CorpusScores(
            bleu=_token_overlap_score(predictions, references),
            chrf=_character_f_score(predictions, references),
            metric_backend="fallback_overlap",
        )

    bleu = sacrebleu.corpus_bleu(predictions, [references]).score
    chrf = sacrebleu.corpus_chrf(predictions, [references]).score
    return CorpusScores(round(bleu, 4), round(chrf, 4), "sacrebleu")


def term_match_rate(predictions: list[str], terms: list[str]) -> float:
    if not predictions:
        return 0.0
    matches = 0
    for prediction, term in zip(predictions, terms):
        if term and term.strip() and term.strip().lower() in prediction.lower():
            matches += 1
    return round(matches / len(predictions), 4)


def _token_overlap_score(predictions: list[str], references: list[str]) -> float:
    scores = []
    for prediction, reference in zip(predictions, references):
        pred_tokens = set(prediction.split())
        ref_tokens = set(reference.split())
        if not ref_tokens:
            scores.append(0.0)
            continue
        scores.append(100 * len(pred_tokens & ref_tokens) / len(ref_tokens))
    return round(sum(scores) / len(scores), 4)


def _character_f_score(predictions: list[str], references: list[str]) -> float:
    scores = []
    for prediction, reference in zip(predictions, references):
        pred_chars = set(prediction)
        ref_chars = set(reference)
        if not pred_chars or not ref_chars:
            scores.append(0.0)
            continue
        precision = len(pred_chars & ref_chars) / len(pred_chars)
        recall = len(pred_chars & ref_chars) / len(ref_chars)
        if precision + recall == 0:
            scores.append(0.0)
        else:
            scores.append(100 * 2 * precision * recall / (precision + recall))
    return round(sum(scores) / len(scores), 4)
