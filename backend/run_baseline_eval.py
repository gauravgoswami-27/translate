#!/usr/bin/env python3
"""Step 5 (GPU): general-domain evaluation on IN22-Gen (all 22 scheduled languages).

* Table 1 of the paper: base model scores on IN22-Gen for every language.
* Forgetting check: with --adapter, the LoRA model is also scored on the domain
  languages, showing whether domain adaptation hurt general translation quality.

IN22-Gen (ai4bharat/IN22-Gen, CC-BY-4.0) is gated: accept its terms on Hugging Face
and export HF_TOKEN.

    python -m backend.run_baseline_eval --adapter models/it2_lora_joint
"""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

from backend.localization_engine import Translator
from backend.localization_engine.languages import (
    DEFAULT_MODEL_NAME,
    DOMAIN_LANGS,
    LANGUAGE_NAMES,
    SCHEDULED_LANGUAGE_TARGETS,
    SOURCE_LANG,
)
from backend.localization_engine.metrics import score_corpus
from backend.localization_engine.paths import RESULTS_DIR


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="IN22-Gen evaluation across the 22 scheduled languages.")
    p.add_argument("--model", default=DEFAULT_MODEL_NAME)
    p.add_argument("--adapter", type=Path, default=None, help="Also score this LoRA adapter on the domain languages.")
    p.add_argument("--skip-base", action="store_true", help="Only score the adapter (base scores computed separately).")
    p.add_argument("--langs", default=None, help="Comma-separated subset (default: all 22).")
    p.add_argument("--limit", type=int, default=None, help="Sentences per language (IN22-Gen has 1024).")
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--output", type=Path, default=RESULTS_DIR / "in22_gen_scores.csv")
    p.add_argument("--chart-output", type=Path, default=RESULTS_DIR / "in22_gen_scores.png")
    return p.parse_args()


def load_in22(limit: int | None):
    from datasets import load_dataset

    ds = load_dataset("ai4bharat/IN22-Gen", split="test", token=os.getenv("HF_TOKEN"))
    if limit:
        ds = ds.select(range(min(limit, len(ds))))
    return ds


def column_for(ds, code: str) -> str:
    for name in (code, f"sentence_{code}", f"{code}_sentence"):
        if name in ds.column_names:
            return name
    raise KeyError(f"No column for {code} in IN22-Gen; columns are: {ds.column_names}")


def main() -> None:
    args = parse_args()
    codes = args.langs.split(",") if args.langs else [lang.code for lang in SCHEDULED_LANGUAGE_TARGETS]
    ds = load_in22(args.limit)
    sources = ds[column_for(ds, SOURCE_LANG)]

    jobs = [] if args.skip_base else [("base", args.model, codes)]
    if args.adapter:
        jobs.append(("lora", str(args.adapter), [c for c in codes if c in DOMAIN_LANGS]))

    rows = []
    for system, model, langs in jobs:
        translator = Translator(model, allow_fallback=False)
        for index, code in enumerate(langs, start=1):
            refs = ds[column_for(ds, code)]
            preds = translator.translate_batch(sources, code, batch_size=args.batch_size)
            scores = score_corpus(preds, refs)
            rows.append(
                {
                    "system": system,
                    "model": model,
                    "language_code": code,
                    "language_name": LANGUAGE_NAMES[code],
                    "bleu": scores.bleu,
                    "chrf_pp": scores.chrf_pp,
                    "num_sentences": len(preds),
                    "benchmark": "IN22-Gen",
                }
            )
            print(f"[{system} {index}/{len(langs)}] {code}: BLEU {scores.bleu:.2f}  chrF++ {scores.chrf_pp:.2f}")
        translator.unload()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {args.output}")
    if not args.skip_base:
        generate_chart([r for r in rows if r["system"] == "base"], args.chart_output)


def generate_chart(rows: list[dict], chart_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = sorted(rows, key=lambda r: r["chrf_pp"], reverse=True)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar([r["language_name"] for r in rows], [r["chrf_pp"] for r in rows], color="#2a6fdb")
    ax.set_ylabel("chrF++")
    ax.set_title("IndicTrans2 en-indic dist-200M on IN22-Gen (English to 22 scheduled languages)")
    ax.tick_params(axis="x", rotation=45)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(chart_path, dpi=300)
    plt.close(fig)
    print(f"Wrote {chart_path}")


if __name__ == "__main__":
    main()
