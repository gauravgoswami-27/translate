#!/usr/bin/env python3
"""Step 1: extract clean English sentences from the official electrician PDFs.

Output: data/corpus_v2/en_sentences.csv with a train/dev/test split.

Splitting is done by blocks of consecutive pages (not by sentence), so text that
is repeated or paraphrased within a chapter cannot leak from train into test.
Near-duplicates of dev/test sentences are additionally removed from train.

Runs on CPU in a few seconds:
    python -m backend.build_corpus
"""

from __future__ import annotations

import argparse
import csv
import random
import re
from collections import Counter
from pathlib import Path

from backend.localization_engine.glossary import ELECTRICIAN_GLOSSARIES, EXTRA_DOMAIN_TERMS
from backend.localization_engine.paths import CORPUS_DIR, RAW_DIR

ABBREVIATIONS = (
    "e.g.", "i.e.", "etc.", "No.", "Nos.", "Fig.", "fig.", "approx.", "Ref.", "Dr.", "Mr.",
    "Sq.", "sq.", "dia.", "min.", "max.", "Vol.", "vs.", "Ex.", "St.", "Co.", "Ltd.",
)
BULLET_RE = re.compile(r"^\s*(?:[•●▪◦\-–*]|\(?[0-9]{1,2}[.)]|\(?[a-z][.)]|\(?[ivx]{1,4}\))\s+")
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"'“])")
GLOSSARY_TERMS = sorted(ELECTRICIAN_GLOSSARIES["hin_Deva"], key=len, reverse=True)
ALL_TERMS = sorted(set(GLOSSARY_TERMS) | set(EXTRA_DOMAIN_TERMS), key=len, reverse=True)
TERM_RE = re.compile(r"\b(" + "|".join(re.escape(t) for t in ALL_TERMS) + r")s?\b", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract English domain sentences and split them.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--output", type=Path, default=CORPUS_DIR / "en_sentences.csv")
    parser.add_argument("--block-pages", type=int, default=10, help="Pages per split unit.")
    parser.add_argument("--test-size", type=int, default=200, help="Sentences to hand to post-editors.")
    parser.add_argument("--dev-size", type=int, default=300)
    parser.add_argument("--min-words", type=int, default=5)
    parser.add_argument("--max-words", type=int, default=45)
    parser.add_argument("--seed", type=int, default=13)
    return parser.parse_args()


# ----------------------------------------------------------------------------
# PDF -> page text -> sentences
# ----------------------------------------------------------------------------

def read_pdf_pages(path: Path) -> list[list[str]]:
    import pymupdf

    with pymupdf.open(path) as doc:
        return [page.get_text("text").splitlines() for page in doc]


def boilerplate_lines(pages: list[list[str]]) -> set[str]:
    """Lines repeated on many pages are running headers/footers."""
    counts: Counter[str] = Counter()
    for page in pages:
        counts.update({line.strip() for line in page if line.strip()})
    threshold = max(3, int(0.05 * len(pages)))
    return {line for line, n in counts.items() if n >= threshold}


def page_segments(lines: list[str], boilerplate: set[str]) -> list[str]:
    """Join wrapped lines into paragraphs; keep headings and bullets separate."""
    segments: list[str] = []
    current = ""
    for raw in lines:
        line = raw.replace("\xad", "").replace("\t", " ").strip()
        if not line or line in boilerplate or re.fullmatch(r"[\divxlcIVXLC .\-]+", line):
            if current:
                segments.append(current)
                current = ""
            continue
        starts_item = bool(BULLET_RE.match(line)) or bool(re.match(r"^(TASK|Rule|Step|Note)\b", line))
        if starts_item and current:
            segments.append(current)
            current = ""
        # A short, unpunctuated line that starts a new block is a heading.
        if not current and len(line.split()) <= 6 and line[0].isupper() and not re.search(r"[.!?:;,]$", line):
            segments.append(line)
            continue
        if current.endswith("-") and not current.endswith(" -"):
            current = current[:-1] + line
        else:
            current = f"{current} {line}".strip()
    if current:
        segments.append(current)
    return segments


def split_sentences(segment: str) -> list[str]:
    protected = segment
    for abbr in ABBREVIATIONS:
        protected = protected.replace(abbr, abbr.replace(".", "<DOT>"))
    return [s.replace("<DOT>", ".") for s in SENT_SPLIT_RE.split(protected)]


def clean_sentence(text: str) -> str:
    text = BULLET_RE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?)])", r"\1", text)
    text = re.sub(r"([(])\s+", r"\1", text)
    return text.strip(" -–•")


def keep_sentence(text: str, min_words: int, max_words: int) -> bool:
    words = text.split()
    if not (min_words <= len(words) <= max_words):
        return False
    letters = sum(ch.isalpha() for ch in text)
    if letters < 0.6 * len(text.replace(" ", "")):
        return False  # tables, formulae, part lists
    upper = sum(ch.isupper() for ch in text)
    if upper > 0.5 * letters:
        return False  # headings in capitals
    if sum(ch.isdigit() for ch in text) > 0.2 * len(text):
        return False
    if re.search(r"https?://|www\.|@|copyright|nimi|all rights reserved|printed in", text, re.IGNORECASE):
        return False
    if not re.search(r"[a-z]{3,}", text):
        return False
    if not re.match(r"^[A-Z0-9\"'“(]", text) or not re.search(r"[.!?]$", text):
        return False  # fragments, headings, broken two-column text
    return True


def normalize_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def shingles(text: str, n: int = 4) -> set[tuple[str, ...]]:
    tokens = normalize_key(text).split()
    return {tuple(tokens[i : i + n]) for i in range(max(1, len(tokens) - n + 1))}


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)

    pdfs = sorted(args.raw_dir.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {args.raw_dir}. Run fetch_real_materials.py first.")

    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for pdf in pdfs:
        pages = read_pdf_pages(pdf)
        boilerplate = boilerplate_lines(pages)
        doc_id = re.sub(r"[^A-Za-z0-9]+", "_", pdf.stem).strip("_")
        kept = 0
        for page_no, lines in enumerate(pages, start=1):
            for segment in page_segments(lines, boilerplate):
                for raw_sentence in split_sentences(segment):
                    sentence = clean_sentence(raw_sentence)
                    if not keep_sentence(sentence, args.min_words, args.max_words):
                        continue
                    key = normalize_key(sentence)
                    if key in seen:
                        continue
                    seen.add(key)
                    terms = sorted({m.group(1).lower() for m in TERM_RE.finditer(sentence)})
                    records.append(
                        {
                            "doc": doc_id,
                            "page": str(page_no),
                            "block": f"{doc_id}:{(page_no - 1) // args.block_pages}",
                            "english_sentence": sentence,
                            "domain_terms": ";".join(terms),
                            "glossary_terms": ";".join(t for t in terms if t in GLOSSARY_TERMS),
                        }
                    )
                    kept += 1
        print(f"{pdf.name}: {len(pages)} pages -> {kept} sentences")

    assign_splits(records, args, rng)
    remove_train_near_duplicates(records)

    records = [r for r in records if r["split"] != "drop"]
    for index, record in enumerate(records, start=1):
        record["id"] = f"elec_{index:05d}"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["id", "split", "english_sentence", "domain_terms", "glossary_terms", "doc", "page", "block"]
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    counts = Counter(r["split"] for r in records)
    with_terms = Counter(r["split"] for r in records if r["domain_terms"])
    print(f"\nWrote {len(records)} sentences to {args.output}")
    for split in ("train", "dev", "test"):
        print(f"  {split:5s}: {counts[split]:5d} sentences ({with_terms[split]} contain domain terms)")


def assign_splits(records: list[dict[str, str]], args: argparse.Namespace, rng: random.Random) -> None:
    """Whole page-blocks go to test, then dev; everything else is train."""
    by_block: dict[str, list[dict[str, str]]] = {}
    for record in records:
        by_block.setdefault(record["block"], []).append(record)
    blocks = sorted(by_block)
    rng.shuffle(blocks)

    for record in records:
        record["split"] = "train"

    test_pool: list[dict[str, str]] = []
    dev_count = 0
    for block in blocks:
        members = by_block[block]
        if len(test_pool) < args.test_size * 2:  # oversample, then pick the most useful ones
            test_pool.extend(members)
        elif dev_count < args.dev_size:
            for record in members:
                record["split"] = "dev"
            dev_count += len(members)
        else:
            break

    # Prefer sentences with domain terminology in the human-verified test set (~75%).
    with_terms = [r for r in test_pool if r["domain_terms"]]
    without_terms = [r for r in test_pool if not r["domain_terms"]]
    rng.shuffle(with_terms)
    rng.shuffle(without_terms)
    n_terms = min(len(with_terms), int(args.test_size * 0.75))
    chosen = with_terms[:n_terms] + without_terms[: args.test_size - n_terms]
    chosen_ids = {id(r) for r in chosen}
    for record in test_pool:
        # Unchosen sentences from test blocks are dropped, never moved into train.
        record["split"] = "test" if id(record) in chosen_ids else "drop"


def remove_train_near_duplicates(records: list[dict[str, str]], threshold: float = 0.7) -> None:
    held_out = [shingles(r["english_sentence"]) for r in records if r["split"] in {"dev", "test"}]
    removed = 0
    for record in records:
        if record["split"] != "train":
            continue
        grams = shingles(record["english_sentence"])
        for other in held_out:
            union = len(grams | other)
            if union and len(grams & other) / union >= threshold:
                record["split"] = "drop"
                removed += 1
                break
    print(f"Removed {removed} train sentences that near-duplicate dev/test sentences.")


if __name__ == "__main__":
    main()
