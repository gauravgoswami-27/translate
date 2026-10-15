#!/usr/bin/env python3
"""Step 2 (GPU): draft target-language references with the IndicTrans2-1B teacher.

* train/dev drafts become synthetic training data (forward translation / sequence-level
  knowledge distillation into the 200M student).
* test drafts are exported as post-editing sheets; the final test references must be
  human post-edited (data/corpus_v2/postedit/test_<lang>.csv).

Resumable: a language whose draft file already exists is skipped.

    python -m backend.generate_drafts --langs hin_Deva,mai_Deva
"""

from __future__ import annotations

import argparse
import csv
import random
import time
from pathlib import Path

from backend.localization_engine import Translator
from backend.localization_engine.languages import DOMAIN_LANGS, LANG_SHORT, TEACHER_MODEL_NAME
from backend.localization_engine.paths import CORPUS_DIR

DRAFT_FIELDS = ["id", "split", "english_sentence", "target_sentence", "target_lang", "glossary_terms", "reference_source"]
POSTEDIT_FIELDS = ["id", "english_sentence", "draft_translation", "post_edited_translation", "glossary_terms", "editor_notes"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Translate the English corpus with the teacher model.")
    parser.add_argument("--langs", default=",".join(DOMAIN_LANGS))
    parser.add_argument("--model", default=TEACHER_MODEL_NAME)
    parser.add_argument("--input", type=Path, default=CORPUS_DIR / "en_sentences.csv")
    parser.add_argument("--output-dir", type=Path, default=CORPUS_DIR)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-tokens", type=int, default=8000, help="Per-batch budget: sentences x source tokens x beams.")
    parser.add_argument("--num-beams", type=int, default=5)
    parser.add_argument("--max-train", type=int, default=None, help="Draft only a random subset of N train sentences (dev/test always kept).")
    parser.add_argument("--limit", type=int, default=None, help="Only the first N sentences (smoke test).")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with args.input.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if args.limit:
        rows = rows[: args.limit]
    if args.max_train:
        train = [r for r in rows if r["split"] == "train"]
        keep = {r["id"] for r in random.Random(0).sample(train, min(args.max_train, len(train)))}
        rows = [r for r in rows if r["split"] != "train" or r["id"] in keep]
    sentences = [row["english_sentence"] for row in rows]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    translator = Translator(args.model, allow_fallback=False)
    print(f"Loaded teacher {args.model} on {translator.device_name}; {len(rows)} sentences per language.")

    for lang in args.langs.split(","):
        draft_path = args.output_dir / f"drafts_{LANG_SHORT[lang]}.csv"
        if draft_path.exists() and not args.overwrite:
            print(f"{lang}: {draft_path.name} exists, skipping (use --overwrite to redo).")
            continue

        start = time.time()
        translations = translator.translate_batch(
            sentences,
            lang,
            batch_size=args.batch_size,
            max_tokens=args.max_tokens,
            num_beams=args.num_beams,
            show_progress=True,
        )
        elapsed = time.time() - start
        print(f"{lang}: translated {len(sentences)} sentences in {elapsed / 60:.1f} min ({len(sentences) / elapsed:.1f} sent/s)")

        tmp_path = draft_path.with_suffix(".tmp")
        with tmp_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=DRAFT_FIELDS)
            writer.writeheader()
            for row, translation in zip(rows, translations):
                writer.writerow(
                    {
                        "id": row["id"],
                        "split": row["split"],
                        "english_sentence": row["english_sentence"],
                        "target_sentence": translation,
                        "target_lang": lang,
                        "glossary_terms": row["glossary_terms"],
                        "reference_source": f"teacher_draft:{args.model}",
                    }
                )
        tmp_path.replace(draft_path)  # atomic: a killed session never leaves a half-written file
        export_postedit_sheet(rows, translations, lang, args.output_dir / "postedit")


def export_postedit_sheet(rows: list[dict[str, str]], translations: list[str], lang: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"test_{LANG_SHORT[lang]}.csv"
    if path.exists():
        print(f"  {path.name} already exists; not overwriting (may contain human edits).")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=POSTEDIT_FIELDS)
        writer.writeheader()
        for row, translation in zip(rows, translations):
            if row["split"] == "test":
                writer.writerow(
                    {
                        "id": row["id"],
                        "english_sentence": row["english_sentence"],
                        "draft_translation": translation,
                        "post_edited_translation": "",
                        "glossary_terms": row["glossary_terms"],
                        "editor_notes": "",
                    }
                )
    print(f"  wrote post-editing sheet {path}")


if __name__ == "__main__":
    main()
