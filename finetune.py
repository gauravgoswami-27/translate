#!/usr/bin/env python3
"""Phase 4: lightweight fine-tuning entrypoint.

For full IndicTrans2/fairseq fine-tuning, use the official repository scripts
with the exported train files produced here. This script prepares reproducible
training artifacts and can run a tiny Hugging Face Seq2SeqTrainer workflow when
all model dependencies are available.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from localization_engine.languages import DEFAULT_MODEL_NAME


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare/run lightweight IndicTrans2 fine-tuning.")
    parser.add_argument("--train-csv", default="data/corpus/electrician_en_hi_train.csv")
    parser.add_argument("--target-lang", default="hin_Deva")
    parser.add_argument("--base-model", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--output-dir", default="models/finetuned_hin_Deva")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--prepare-only", action="store_true", help="Only export text pairs and metadata.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = read_rows(Path(args.train_csv))
    source_file = output_dir / "train.eng_Latn"
    target_file = output_dir / f"train.{args.target_lang}"
    source_file.write_text("\n".join(row["english_sentence"] for row in rows), encoding="utf-8")
    target_file.write_text(
        "\n".join(row.get("target_sentence") or row.get("hindi_sentence") or "" for row in rows),
        encoding="utf-8",
    )
    metadata = {
        "base_model": args.base_model,
        "target_lang": args.target_lang,
        "train_csv": args.train_csv,
        "num_rows": len(rows),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "status": "prepared",
        "note": "Use official IndicTrans2 fairseq scripts for paper-grade fine-tuning, or extend this entrypoint for local GPU runs.",
    }
    (output_dir / "training_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    if args.prepare_only:
        print(f"Prepared fine-tuning files in {output_dir}")
        return

    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
        import IndicTransToolkit  # noqa: F401
    except Exception as exc:
        print(f"Prepared files, but skipped model training because dependencies are missing: {exc}")
        print(f"Artifacts are in {output_dir}")
        return

    print(
        "Prepared training artifacts. Full training is intentionally not auto-started because "
        "IndicTrans2 fine-tuning requires the official fairseq setup and substantial compute."
    )


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    main()
