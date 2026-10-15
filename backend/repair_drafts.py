#!/usr/bin/env python3
"""Experiment 2, step 1 (GPU): make the teacher drafts follow the formal glossary.

For every train/dev draft whose English source contains glossary terms but whose
draft does not use the glossary form for all of them, the teacher (IndicTrans2-1B)
re-translates the sentence with lexically constrained beam search, forcing the
glossary term (or one of its variants) for each term. Each repaired output is then
validated, because constrained search can satisfy a constraint by tacking the term on
after the sentence:
  * every glossary term must be present (normalised spelling);
  * the term must not appear only after the final sentence punctuation;
  * length must stay within 0.7-1.5x the original draft (in words).
Rows that fail validation are marked ``failed`` and excluded from training.

Test drafts are NOT touched: they are the post-editing seeds, and constraining them
would bias the human references towards the terminology-aware system.

Output: data/corpus_v2/drafts_<lang>_formal.csv (raw drafts stay unchanged), with a
``term_repair`` column in {kept, repaired, failed}. Resumable per language.

    python -m backend.repair_drafts --langs hin_Deva,mai_Deva
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from pathlib import Path

from backend.localization_engine import Translator
from backend.localization_engine.data import read_csv
from backend.localization_engine.glossary import ACTIVE_REGISTER, constraint_forms
from backend.localization_engine.languages import DOMAIN_LANGS, LANG_SHORT, TEACHER_MODEL_NAME
from backend.localization_engine.metrics import normalize_indic, term_forms
from backend.localization_engine.paths import CORPUS_DIR, RESULTS_DIR

SENTENCE_END = re.compile(r"[।.!?]")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Terminology-constrained repair of teacher drafts.")
    p.add_argument("--langs", default=",".join(DOMAIN_LANGS))
    p.add_argument("--model", default=TEACHER_MODEL_NAME)
    p.add_argument("--splits", default="train,dev")
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--max-tokens", type=int, default=6000)
    p.add_argument("--num-beams", type=int, default=5)
    p.add_argument("--limit", type=int, default=None, help="Repair at most N sentences per language (smoke test).")
    p.add_argument("--output-dir", type=Path, default=CORPUS_DIR)
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()


def missing_terms(draft: str, terms: list[str], lang: str) -> list[str]:
    normalized = normalize_indic(draft)
    return [t for t in terms if term_forms(t, lang) and not any(f in normalized for f in term_forms(t, lang))]


def validate(repaired: str, original: str, terms: list[str], lang: str) -> str:
    """Empty string if the repaired draft is acceptable, otherwise the rejection reason."""
    if missing_terms(repaired, terms, lang):
        return "constraint_not_met"
    normalized = normalize_indic(repaired).rstrip()
    ends = [m.end() for m in SENTENCE_END.finditer(normalized)]
    body_end = ends[-1] if ends and ends[-1] < len(normalized) else len(normalized)
    body = normalized[:body_end]
    for term in terms:
        forms = term_forms(term, lang)
        if forms and not any(f in body for f in forms):
            return "term_appended_after_sentence"
    ratio = len(repaired.split()) / max(1, len(original.split()))
    if not 0.7 <= ratio <= 1.5:
        return f"length_ratio_{ratio:.2f}"
    return ""


def main() -> None:
    args = parse_args()
    splits = set(args.splits.split(","))
    translator = None
    stats: dict[str, dict] = {}

    for lang in args.langs.split(","):
        short = LANG_SHORT[lang]
        out_path = args.output_dir / f"drafts_{short}_formal.csv"
        if out_path.exists() and not args.overwrite:
            print(f"{lang}: {out_path.name} exists, skipping.")
            continue
        rows = read_csv(CORPUS_DIR / f"drafts_{short}.csv")

        todo = []
        for i, row in enumerate(rows):
            row["term_repair"], row["repair_note"] = "kept", ""
            terms = [t for t in row["glossary_terms"].split(";") if t]
            if row["split"] in splits and terms and missing_terms(row["target_sentence"], terms, lang):
                todo.append((i, [t for t in terms if constraint_forms(t, lang)]))
        if args.limit:
            todo = todo[: args.limit]
        print(f"{lang}: {len(todo)} drafts need terminology repair ({ACTIVE_REGISTER} register)")

        if todo:
            if translator is None:
                translator = Translator(args.model, allow_fallback=False)
            start = time.time()
            repaired = translator.translate_batch(
                [rows[i]["english_sentence"] for i, _ in todo],
                lang,
                batch_size=args.batch_size,
                max_tokens=args.max_tokens,
                num_beams=args.num_beams,
                show_progress=True,
                constraints=[[constraint_forms(t, lang) for t in terms] for _, terms in todo],
            )
            minutes = (time.time() - start) / 60
            for (i, terms), text in zip(todo, repaired):
                reason = validate(text, rows[i]["target_sentence"], terms, lang)
                rows[i]["repair_note"] = reason or f"was: {rows[i]['target_sentence']}"
                if reason:
                    rows[i]["term_repair"] = "failed"
                else:
                    rows[i]["term_repair"] = "repaired"
                    rows[i]["target_sentence"] = text
                    rows[i]["reference_source"] = f"teacher_constrained:{args.model}"
        else:
            minutes = 0.0

        counts = {k: sum(r["term_repair"] == k for r in rows) for k in ("kept", "repaired", "failed")}
        reasons: dict[str, int] = {}
        for r in rows:
            if r["term_repair"] == "failed":
                key = r["repair_note"].split("_")[0] if r["repair_note"].startswith("length") else r["repair_note"]
                reasons[key] = reasons.get(key, 0) + 1
        stats[lang] = {"needed_repair": len(todo), **counts, "failure_reasons": reasons, "minutes": round(minutes, 1)}
        print(f"{lang}: {stats[lang]}")

        tmp = out_path.with_suffix(".tmp")
        with tmp.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        tmp.replace(out_path)

    if stats:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stats_path = RESULTS_DIR / f"term_repair_stats_{'_'.join(LANG_SHORT[l] for l in stats)}.json"
        stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {stats_path}")


if __name__ == "__main__":
    main()
