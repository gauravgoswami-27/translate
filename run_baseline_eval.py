#!/usr/bin/env python3
"""Phase 2: baseline evaluation over scheduled Indic languages."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from localization_engine import Translator
from localization_engine.languages import DEFAULT_MODEL_NAME, LANGUAGE_NAMES, SCHEDULED_LANGUAGE_TARGETS
from localization_engine.metrics import score_corpus


SAMPLE_EN = [
    "Switch off the main supply before opening the control panel.",
    "Check the insulation resistance with a megger.",
    "Use a circuit breaker of the correct rating.",
    "Connect the neutral wire to the terminal block.",
    "Wear safety shoes while working near live wires.",
]

SAMPLE_REFERENCES = {
    "hin_Deva": [
        "नियंत्रण पैनल खोलने से पहले मुख्य आपूर्ति बंद करें।",
        "मेगर से इन्सुलेशन प्रतिरोध की जांच करें।",
        "सही रेटिंग का सर्किट ब्रेकर उपयोग करें।",
        "न्यूट्रल तार को टर्मिनल ब्लॉक से जोड़ें।",
        "लाइव तारों के पास काम करते समय सुरक्षा जूते पहनें।",
    ]
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run baseline translation evaluation.")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--output", default="results/baseline_scores.csv")
    parser.add_argument("--limit-languages", type=int, default=None, help="Useful for smoke tests.")
    parser.add_argument("--force-fallback", action="store_true")
    parser.add_argument(
        "--allow-sample-fallback",
        action="store_true",
        help="Use bundled smoke-test sentences if IN22 data is not available.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    languages = list(SCHEDULED_LANGUAGE_TARGETS)
    if args.limit_languages:
        languages = languages[: args.limit_languages]

    translator = Translator(model_name_or_path=args.model, force_fallback=args.force_fallback)
    rows = []
    for language in languages:
        inputs, refs, data_source = load_eval_set(language.code, allow_sample=args.allow_sample_fallback)
        predictions = [translator.translate(sentence, language.code).translated_text for sentence in inputs]
        scores = score_corpus(predictions, refs)
        rows.append(
            {
                "language_code": language.code,
                "language_name": LANGUAGE_NAMES[language.code],
                "bleu": scores.bleu,
                "chrf": scores.chrf,
                "metric_backend": scores.metric_backend,
                "translation_backend": translator.backend,
                "num_sentences": len(inputs),
                "data_source": data_source,
            }
        )

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {output_path}")


def load_eval_set(target_lang: str, allow_sample: bool) -> tuple[list[str], list[str], str]:
    candidates = [
        Path("data/in22") / f"eng_Latn-{target_lang}.csv",
        Path("data/in22") / f"{target_lang}.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            with candidate.open(encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                inputs = []
                refs = []
                for row in reader:
                    inputs.append(row.get("english") or row.get("source") or row.get("src") or "")
                    refs.append(row.get("reference") or row.get("target") or row.get(target_lang) or "")
            return inputs, refs, str(candidate)

    if not allow_sample:
        raise FileNotFoundError(
            f"IN22 CSV for {target_lang} not found in data/in22. "
            "Download IN22 or rerun with --allow-sample-fallback for a smoke test."
        )

    refs = SAMPLE_REFERENCES.get(target_lang, SAMPLE_EN)
    return SAMPLE_EN, refs, "bundled_smoke_test"


if __name__ == "__main__":
    main()
