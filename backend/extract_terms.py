#!/usr/bin/env python3
"""Phase 3: build the electrician-domain corpus.

The default command creates a transparent seed corpus for reproducible local
development. Add official PDFs/text files to data/raw and pass --from-raw to
extract candidate terms while keeping source provenance.
"""

from __future__ import annotations

import argparse
import csv
import random
import re
from pathlib import Path

from backend.localization_engine.glossary import ELECTRICIAN_GLOSSARIES


TEMPLATES = [
    ("Inspect the {term} before starting the practical task.", "व्यावहारिक कार्य शुरू करने से पहले {term} की जांच करें।"),
    ("The trainee must identify the correct {term}.", "प्रशिक्षु को सही {term} की पहचान करनी चाहिए।"),
    ("Record the reading of the {term} in the job sheet.", "जॉब शीट में {term} की रीडिंग दर्ज करें।"),
    ("Use proper PPE while handling the {term}.", "{term} को संभालते समय उचित पीपीई का उपयोग करें।"),
    ("Replace the damaged {term} only after isolating the supply.", "आपूर्ति अलग करने के बाद ही खराब {term} बदलें।"),
    ("Explain the purpose of {term} during wiring practice.", "वायरिंग अभ्यास के दौरान {term} का उद्देश्य समझाएं।"),
    ("Check whether the {term} is securely connected.", "जांचें कि {term} सुरक्षित रूप से जुड़ा है या नहीं।"),
    ("Do not touch the {term} with wet hands.", "{term} को गीले हाथों से न छुएं।"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create electrician-domain parallel corpora.")
    parser.add_argument("--lang", default="hin_Deva")
    parser.add_argument("--rows", type=int, default=240)
    parser.add_argument("--output-dir", default="data/corpus")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--from-raw", action="store_true", help="Extract candidate terms from text/PDF-derived files in data/raw.")
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = extract_from_raw(Path(args.raw_dir), args.lang) if args.from_raw else []
    rows.extend(generate_seed_rows(args.lang, max(0, args.rows - len(rows))))
    rows = rows[: args.rows]

    random.shuffle(rows)
    split_index = max(1, int(len(rows) * 0.8))
    train_rows = rows[:split_index]
    test_rows = rows[split_index:]

    write_csv(output_dir / f"electrician_en_{lang_suffix(args.lang)}.csv", rows)
    write_csv(output_dir / f"electrician_en_{lang_suffix(args.lang)}_train.csv", train_rows)
    write_csv(output_dir / f"electrician_en_{lang_suffix(args.lang)}_test.csv", test_rows)
    print(f"Wrote {len(train_rows)} train and {len(test_rows)} test rows to {output_dir}")


def generate_seed_rows(lang: str, count: int) -> list[dict[str, str]]:
    glossary = ELECTRICIAN_GLOSSARIES.get(lang) or ELECTRICIAN_GLOSSARIES["hin_Deva"]
    terms = list(glossary.items())
    rows = []
    for index in range(count):
        english_term, target_term = terms[index % len(terms)]
        english_template, target_template = TEMPLATES[index % len(TEMPLATES)]
        rows.append(
            {
                "id": f"{lang_suffix(lang)}_seed_{index + 1:04d}",
                "english_term": english_term,
                "target_term": target_term,
                "hindi_term": target_term if lang == "hin_Deva" else "",
                "english_sentence": english_template.format(term=english_term),
                "target_sentence": target_template.format(term=target_term),
                "hindi_sentence": target_template.format(term=target_term) if lang == "hin_Deva" else "",
                "target_lang": lang,
                "source": "machine_seed_glossary_for_method_development",
                "needs_manual_review": "True",
            }
        )
    return rows


def extract_from_raw(raw_dir: Path, lang: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not raw_dir.exists():
        return rows
    glossary = ELECTRICIAN_GLOSSARIES.get(lang) or ELECTRICIAN_GLOSSARIES["hin_Deva"]
    pattern = re.compile("|".join(re.escape(term) for term in glossary), flags=re.IGNORECASE)
    for path in raw_dir.rglob("*.txt"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match_index, match in enumerate(pattern.finditer(text), start=1):
            english_term = match.group(0).lower()
            target_term = glossary.get(english_term, glossary.get(english_term.title(), ""))
            sentence = surrounding_sentence(text, match.start())
            clean_sentence = re.sub(r"\s+", " ", sentence).strip()
            if len(clean_sentence) < 15 or len(clean_sentence) > 200:
                continue

            tgt_sentence = clean_sentence
            if english_term and target_term:
                tgt_sentence = re.sub(re.escape(english_term), target_term, clean_sentence, flags=re.IGNORECASE)

            rows.append(
                {
                    "id": f"{lang_suffix(lang)}_raw_{path.stem[:15]}_{match_index:04d}",
                    "english_term": english_term,
                    "target_term": target_term,
                    "hindi_term": target_term if lang == "hin_Deva" else "",
                    "english_sentence": clean_sentence,
                    "target_sentence": tgt_sentence,
                    "hindi_sentence": tgt_sentence if lang == "hin_Deva" else "",
                    "target_lang": lang,
                    "source": str(path),
                    "needs_manual_review": "True",
                }
            )
    return rows


def surrounding_sentence(text: str, position: int) -> str:
    start = max(text.rfind(".", 0, position), text.rfind("\n", 0, position)) + 1
    end_candidates = [index for index in (text.find(".", position), text.find("\n", position)) if index != -1]
    end = min(end_candidates) if end_candidates else min(len(text), position + 180)
    return text[start:end].strip()


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "id",
        "english_term",
        "target_term",
        "hindi_term",
        "english_sentence",
        "target_sentence",
        "hindi_sentence",
        "target_lang",
        "source",
        "needs_manual_review",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def lang_suffix(lang: str) -> str:
    return {
        "hin_Deva": "hi",
        "gom_Deva": "gom",
        "mai_Deva": "mai",
        "doi_Deva": "doi",
    }.get(lang, lang)


if __name__ == "__main__":
    main()
