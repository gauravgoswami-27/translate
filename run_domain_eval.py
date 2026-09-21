#!/usr/bin/env python3
"""Phase 5: compare baseline and domain model behavior."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from localization_engine import Translator
from localization_engine.languages import DEFAULT_MODEL_NAME
from localization_engine.metrics import score_corpus, term_match_rate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate baseline vs fine-tuned/domain model.")
    parser.add_argument("--test-csv", default="data/corpus/electrician_en_hi_test.csv")
    parser.add_argument("--target-lang", default="hin_Deva")
    parser.add_argument("--baseline-model", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--finetuned-model", default="models/finetuned_hin_Deva")
    parser.add_argument("--output", default="results/comparison_scores.csv")
    parser.add_argument("--examples-output", default="results/qualitative_examples.csv")
    parser.add_argument("--force-fallback", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_rows(Path(args.test_csv))
    inputs = [row["english_sentence"] for row in rows]
    refs = [row.get("target_sentence") or row.get("hindi_sentence") or "" for row in rows]
    terms = [row.get("target_term") or row.get("hindi_term") or "" for row in rows]

    baseline = Translator(args.baseline_model, force_fallback=args.force_fallback)
    finetuned_path = Path(args.finetuned_model)
    finetuned = Translator(
        str(finetuned_path) if finetuned_path.exists() else args.baseline_model,
        force_fallback=args.force_fallback or not finetuned_path.exists(),
    )

    baseline_predictions = [baseline.translate(text, args.target_lang).translated_text for text in inputs]
    finetuned_predictions = [finetuned.translate(text, args.target_lang).translated_text for text in inputs]
    baseline_scores = score_corpus(baseline_predictions, refs)
    finetuned_scores = score_corpus(finetuned_predictions, refs)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_rows = [
        {
            "system": "baseline",
            "target_lang": args.target_lang,
            "bleu": baseline_scores.bleu,
            "chrf": baseline_scores.chrf,
            "term_match_rate": term_match_rate(baseline_predictions, terms),
            "metric_backend": baseline_scores.metric_backend,
            "translation_backend": baseline.backend,
            "model": args.baseline_model,
            "num_sentences": len(inputs),
        },
        {
            "system": "fine_tuned_or_domain",
            "target_lang": args.target_lang,
            "bleu": finetuned_scores.bleu,
            "chrf": finetuned_scores.chrf,
            "term_match_rate": term_match_rate(finetuned_predictions, terms),
            "metric_backend": finetuned_scores.metric_backend,
            "translation_backend": finetuned.backend,
            "model": str(finetuned_path),
            "num_sentences": len(inputs),
        },
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison_rows[0].keys()))
        writer.writeheader()
        writer.writerows(comparison_rows)

    write_examples(Path(args.examples_output), rows, baseline_predictions, finetuned_predictions, refs)
    print(f"Wrote {output_path} and {args.examples_output}")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_examples(path: Path, rows: list[dict[str, str]], baseline: list[str], finetuned: list[str], refs: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    examples = []
    for row, base_prediction, tuned_prediction, reference in zip(rows[:10], baseline[:10], finetuned[:10], refs[:10]):
        examples.append(
            {
                "id": row["id"],
                "english_sentence": row["english_sentence"],
                "reference": reference,
                "baseline_prediction": base_prediction,
                "fine_tuned_prediction": tuned_prediction,
                "target_term": row.get("target_term") or row.get("hindi_term") or "",
            }
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(examples[0].keys()))
        writer.writeheader()
        writer.writerows(examples)


if __name__ == "__main__":
    main()
