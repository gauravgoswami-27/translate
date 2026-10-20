#!/usr/bin/env python3
"""Detached vs attached case endings after glossary terms in system outputs (CPU only).

Placeholder repair (run 5) made the teacher write Maithili/Konkani case endings as separate
words after the inserted term ("विद्युतरोधन क"); the run-5 model learned it. Run 6 retrains
on case-fixed drafts. This script counts, per system and language, how often a glossary
term is followed by a *detached* ending vs an *attached* one.

    python -m backend.analyze_case_endings backend/results/domain_predictions_UNVERIFIED_run5_hy.csv \
        backend/results/domain_predictions_UNVERIFIED_run6a.csv
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from backend.localization_engine.glossary import ELECTRICIAN_GLOSSARIES, TERM_VARIANTS
from backend.localization_engine.metrics import _stem
from backend.localization_engine.paths import RESULTS_DIR
from backend.localization_engine.translator import ATTACHED_CASE_SUFFIXES

END = r"(?=[\s।.,;:!?)]|$)"

# Dravidian languages have no attach list (suffixes join with sandhi), so detached forms are
# probed with common case suffixes and "attached" counts any directly inflected term
# (term immediately followed by a letter of the same script).
DRAVIDIAN_PROBES = {
    "tam_Taml": ("ஐ", "இல்", "க்கு", "ஆல்", "இன்", "உடன்", "யை", "யில்", "த்தை", "த்தில்", "த்தின்", "ஆக"),
    "tel_Telu": ("ను", "కు", "లో", "తో", "ని", "కి", "యొక్క", "పై"),
    "kan_Knda": ("ಅನ್ನು", "ವನ್ನು", "ಗೆ", "ಕ್ಕೆ", "ಇಂದ", "ದಿಂದ", "ದ", "ನ", "ಅಲ್ಲಿ", "ದಲ್ಲಿ"),
}
SCRIPT_LETTERS = {"tam_Taml": "\u0B80-\u0BFF", "tel_Telu": "\u0C00-\u0C7F", "kan_Knda": "\u0C80-\u0CFF"}


def patterns(lang: str):
    terms = sorted(
        set(ELECTRICIAN_GLOSSARIES[lang].values()) | {v for vs in TERM_VARIANTS[lang].values() for v in vs},
        key=len,
        reverse=True,
    )
    term_re = "|".join(map(re.escape, terms))
    if lang in DRAVIDIAN_PROBES:
        probe_re = "|".join(map(re.escape, DRAVIDIAN_PROBES[lang]))
        # inflection changes the stem ending, so "attached" matches the term or its stem + more letters
        stems = sorted(set(terms) | {st for st in map(_stem, terms) if st}, key=len, reverse=True)
        stem_re = "|".join(map(re.escape, stems))
        return re.compile(f"(?:{term_re}) (?:{probe_re}){END}"), re.compile(f"(?:{stem_re})[{SCRIPT_LETTERS[lang]}]")
    suffix_re = "|".join(map(re.escape, ATTACHED_CASE_SUFFIXES[lang]))
    return re.compile(f"(?:{term_re}) (?:{suffix_re}){END}"), re.compile(f"(?:{term_re})(?:{suffix_re}){END}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("predictions", nargs="+", type=Path)
    p.add_argument("--output", type=Path, default=RESULTS_DIR / "case_endings.csv")
    args = p.parse_args()

    out = []
    for path in args.predictions:
        with path.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        systems = [c.removesuffix("_prediction") for c in rows[0] if c.endswith("_prediction")]
        for lang in [*ATTACHED_CASE_SUFFIXES, *DRAVIDIAN_PROBES]:
            lang_rows = [r for r in rows if r["target_lang"] == lang]
            if not lang_rows:
                continue
            detached_re, attached_re = patterns(lang)
            for system in systems:
                texts = [r[f"{system}_prediction"] for r in lang_rows]
                detached = sum(len(detached_re.findall(t)) for t in texts)
                attached = sum(len(attached_re.findall(t)) for t in texts)
                total = detached + attached
                out.append(
                    {
                        "file": path.name,
                        "target_lang": lang,
                        "system": system,
                        "detached": detached,
                        "attached": attached,
                        "detached_pct": round(100 * detached / total, 1) if total else "",
                    }
                )
                print(f"{lang} {system:28s} detached {detached:3d}  attached {attached:3d}  ({out[-1]['detached_pct']}% detached)")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out[0]))
        writer.writeheader()
        writer.writerows(out)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
