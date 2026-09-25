#!/usr/bin/env python3
"""Phase 5: compare baseline and domain model behavior across target languages."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from backend.localization_engine import Translator
from backend.localization_engine.languages import DEFAULT_MODEL_NAME, PRIMARY_DOMAIN_LANGS, STRETCH_DOMAIN_LANGS
from backend.localization_engine.metrics import score_corpus, term_match_rate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate baseline vs fine-tuned domain models across target languages.")
    parser.add_argument("--baseline-model", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--output", default="results/comparison_scores.csv")
    parser.add_argument("--examples-output", default="results/qualitative_examples.csv")
    parser.add_argument("--force-fallback", action="store_true")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    args = parse_args()
    target_languages = list(PRIMARY_DOMAIN_LANGS) + list(STRETCH_DOMAIN_LANGS)
    
    baseline = Translator(args.baseline_model, force_fallback=args.force_fallback)
    comparison_rows = []
    all_examples = []

    for target_lang in target_languages:
        lang_suffix = {"hin_Deva": "hi", "gom_Deva": "gom", "mai_Deva": "mai", "doi_Deva": "doi"}.get(target_lang, target_lang)
        test_csv_path = Path("data/corpus") / f"electrician_en_{lang_suffix}_test.csv"
        
        if not test_csv_path.exists():
            print(f"Skipping {target_lang}: test CSV {test_csv_path} not found.")
            continue

        print(f"Evaluating target language {target_lang} from {test_csv_path}...")
        rows = read_rows(test_csv_path)
        inputs = [row["english_sentence"] for row in rows]
        refs = [row.get("target_sentence") or row.get("hindi_sentence") or "" for row in rows]
        terms = [row.get("target_term") or row.get("hindi_term") or "" for row in rows]

        finetuned_path = Path("models") / f"finetuned_{target_lang}"
        finetuned = Translator(
            str(finetuned_path) if finetuned_path.exists() else args.baseline_model,
            force_fallback=args.force_fallback or not finetuned_path.exists(),
        )

        baseline_preds = [baseline.translate(text, target_lang).translated_text for text in inputs]
        finetuned_preds = [finetuned.translate(text, target_lang).translated_text for text in inputs]

        b_scores = score_corpus(baseline_preds, refs)
        f_scores = score_corpus(finetuned_preds, refs)

        comparison_rows.extend([
            {
                "system": "baseline",
                "target_lang": target_lang,
                "bleu": round(b_scores.bleu, 4),
                "chrf": round(b_scores.chrf, 4),
                "term_match_rate": round(term_match_rate(baseline_preds, terms), 4),
                "metric_backend": b_scores.metric_backend,
                "translation_backend": baseline.backend,
                "model": args.baseline_model,
                "num_sentences": len(inputs),
            },
            {
                "system": "fine_tuned_domain",
                "target_lang": target_lang,
                "bleu": round(f_scores.bleu, 4),
                "chrf": round(f_scores.chrf, 4),
                "term_match_rate": round(term_match_rate(finetuned_preds, terms), 4),
                "metric_backend": f_scores.metric_backend,
                "translation_backend": finetuned.backend,
                "model": str(finetuned_path),
                "num_sentences": len(inputs),
            },
        ])

        for row, base_p, tuned_p, ref in zip(rows[:5], baseline_preds[:5], finetuned_preds[:5], refs[:5]):
            all_examples.append(
                {
                    "target_lang": target_lang,
                    "id": row["id"],
                    "english_sentence": row["english_sentence"],
                    "reference": ref,
                    "baseline_prediction": base_p,
                    "fine_tuned_prediction": tuned_p,
                    "target_term": row.get("target_term") or row.get("hindi_term") or "",
                }
            )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison_rows[0].keys()))
        writer.writeheader()
        writer.writerows(comparison_rows)

    examples_path = Path(args.examples_output)
    with examples_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(all_examples[0].keys()))
        writer.writeheader()
        writer.writerows(all_examples)

    print(f"Wrote multi-language comparison results to {output_path} and {examples_path}")


if __name__ == "__main__":
    main()
