#!/usr/bin/env python3
"""How consistently does the teacher render glossary terms in its drafts? (CPU only)

For every glossary term and language: in how many train/dev drafts whose English source
contains the term does the draft use an accepted glossary form (after orthographic
normalisation)? Low rates mean the student is distilled on inconsistent or wrong
terminology (e.g. "phase" -> चरण "stage", "earthing" -> पृथ्वी "planet Earth").

    python -m backend.analyze_terminology
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

from backend.localization_engine.data import read_csv
from backend.localization_engine.glossary import ELECTRICIAN_GLOSSARIES
from backend.localization_engine.languages import DOMAIN_LANGS, LANG_SHORT
from backend.localization_engine.metrics import normalize_indic, term_forms
from backend.localization_engine.paths import CORPUS_DIR, RESULTS_DIR


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--langs", default=",".join(DOMAIN_LANGS))
    p.add_argument("--splits", default="train,dev")
    p.add_argument("--output", type=Path, default=RESULTS_DIR / "teacher_term_consistency.csv")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    splits = set(args.splits.split(","))
    rows = []
    for lang in args.langs.split(","):
        drafts = [r for r in read_csv(CORPUS_DIR / f"drafts_{LANG_SHORT[lang]}.csv") if r["split"] in splits]
        normalized = [normalize_indic(r["target_sentence"]) for r in drafts]
        terms_of = [set(r["glossary_terms"].split(";")) for r in drafts]
        lang_hits = lang_total = 0
        for term in ELECTRICIAN_GLOSSARIES[lang]:
            with_term = [i for i, terms in enumerate(terms_of) if term in terms]
            if not with_term:
                continue
            forms = term_forms(term, lang)
            misses = [i for i in with_term if not any(f in normalized[i] for f in forms)]
            # Most frequent words in misses = what the teacher used instead (for manual inspection).
            instead = Counter(w for i in misses for w in set(re.findall(r"\S+", drafts[i]["target_sentence"])))
            hits = len(with_term) - len(misses)
            rows.append(
                {
                    "target_lang": lang,
                    "english_term": term,
                    "glossary_form": ELECTRICIAN_GLOSSARIES[lang][term],
                    "sentences": len(with_term),
                    "teacher_uses_glossary_pct": round(100 * hits / len(with_term), 1),
                    "frequent_words_in_misses": " ".join(w for w, _ in instead.most_common(8)),
                }
            )
            lang_hits += hits
            lang_total += len(with_term)
        print(f"{lang}: teacher uses the glossary form in {lang_hits}/{lang_total} drafts ({100 * lang_hits / lang_total:.1f}%)")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["target_lang"], r["teacher_uses_glossary_pct"])))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
