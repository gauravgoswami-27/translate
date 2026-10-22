"""Loading the v2 corpus (drafts, post-edited test sets)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .languages import LANG_SHORT
from .paths import CORPUS_DIR


@dataclass
class TestSet:
    ids: list[str]
    sources: list[str]
    references: list[str]
    glossary_terms: list[list[str]]
    reference_type: str  # "human_post_edited" or "teacher_draft_UNVERIFIED"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_pairs(lang: str, split: str, corpus_dir: Path = CORPUS_DIR, variant: str = "") -> tuple[list[str], list[str]]:
    """(source, target) pairs for train/dev from the teacher drafts; empty pairs are dropped together.

    ``variant`` selects drafts_<lang>_<variant>.csv (e.g. "formal" = terminology-repaired drafts);
    rows whose terminology repair failed are excluded.
    """
    suffix = f"_{variant}" if variant else ""
    path = corpus_dir / f"drafts_{LANG_SHORT[lang]}{suffix}.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found - run generate_drafts.py (or repair_drafts.py) first.")
    sources, targets = [], []
    for row in read_csv(path):
        if row["split"] != split or row.get("term_repair") == "failed":
            continue
        src, tgt = row["english_sentence"].strip(), row["target_sentence"].strip()
        if src and tgt:  # filter the pair, never one side alone (keeps alignment)
            sources.append(src)
            targets.append(tgt)
    return sources, targets


def load_test_set(lang: str, corpus_dir: Path = CORPUS_DIR, allow_unverified: bool = True) -> TestSet:
    """Prefer the human post-edited sheet; fall back to teacher drafts, clearly labelled."""
    sheet = corpus_dir / "postedit" / f"test_{LANG_SHORT[lang]}.csv"
    if sheet.exists():
        rows = read_csv(sheet)
        edited = [r for r in rows if r["post_edited_translation"].strip()]
        if rows and len(edited) == len(rows):
            return TestSet(
                ids=[r["id"] for r in rows],
                sources=[r["english_sentence"] for r in rows],
                references=[r["post_edited_translation"].strip() for r in rows],
                glossary_terms=[_split_terms(r["glossary_terms"]) for r in rows],
                reference_type="human_post_edited",
            )
        if edited:
            print(f"[{lang}] post-editing incomplete ({len(edited)}/{len(rows)}); using teacher drafts.")

    if not allow_unverified:
        raise RuntimeError(f"No complete human post-edited test set for {lang} at {sheet}.")
    rows = [r for r in read_csv(corpus_dir / f"drafts_{LANG_SHORT[lang]}.csv") if r["split"] == "test"]
    return TestSet(
        ids=[r["id"] for r in rows],
        sources=[r["english_sentence"] for r in rows],
        references=[r["target_sentence"] for r in rows],
        glossary_terms=[_split_terms(r["glossary_terms"]) for r in rows],
        reference_type="teacher_draft_UNVERIFIED",
    )


def _split_terms(value: str) -> list[str]:
    return [t for t in (value or "").split(";") if t]
