#!/usr/bin/env python3
"""Per-term terminology analysis of saved predictions and teacher drafts (CPU only).

Writes three tables to backend/results/:
  term_breakdown.csv     compliance per (language, system, term)
  term_compliance_macro.csv
                         per (language, system): pooled compliance (every occurrence counts),
                         macro compliance (mean over terms, each term counts once), and pooled
                         compliance without "conduit", which alone is 46% of the test-set term
                         occurrences (one test page-block comes from a conduit-wiring chapter)
  wrong_sense.csv        rate of wrong-sense renderings (an actual error, unlike a loanword):
                         "phase" -> चरण (stage), "earthing" -> पृथ्वी/मिट्टी/धरती (planet/soil),
                         "live wire" -> जीवित/जींदे (living), in teacher train/dev drafts and in
                         system outputs on the test set

    python -m backend.analyze_term_breakdown backend/results/domain_predictions_UNVERIFIED_run5_hy.csv \\
        backend/results/domain_predictions_UNVERIFIED_run6a.csv
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

from backend.localization_engine.data import load_test_set, read_csv
from backend.localization_engine.languages import LANG_SHORT
from backend.localization_engine.metrics import normalize_indic, term_forms
from backend.localization_engine.paths import CORPUS_DIR, RESULTS_DIR

LANGS = ("hin_Deva", "gom_Deva", "mai_Deva", "doi_Deva")
# Wrong-sense renderings: a different meaning, not just a different register.
WRONG_SENSE = {
    "three phase": r"चरण",
    "single phase": r"चरण",
    "earthing": r"पृथ्वी|मिट्टी|माटी|धरती|मातीं|भूंय",
    "live wire": r"जीवित|जीवंत|जीवत|जींदे|जिवंत",
}


def load_predictions(paths: list[Path]):
    """{(lang, id): {system: text}} merged over files (later files add systems)."""
    merged: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    systems: list[str] = []
    for path in paths:
        rows = read_csv(path)
        file_systems = [c.removesuffix("_prediction") for c in rows[0] if c.endswith("_prediction")]
        systems += [s for s in file_systems if s not in systems]
        for r in rows:
            for s in file_systems:
                merged[(r["target_lang"], r["id"])][s] = r[f"{s}_prediction"]
    return merged, systems


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("predictions", nargs="+", type=Path)
    p.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    args = p.parse_args()
    preds, systems = load_predictions(args.predictions)

    per_term = []
    macro = []
    for lang in LANGS:
        ts = load_test_set(lang)
        for system in systems:
            hits: dict[str, list[int]] = defaultdict(list)
            for sid, terms in zip(ts.ids, ts.glossary_terms):
                out = normalize_indic(preds[(lang, sid)].get(system, ""))
                for term in terms:
                    forms = term_forms(term, lang)
                    if forms:
                        hits[term].append(int(any(f in out for f in forms)))
            for term, h in sorted(hits.items()):
                per_term.append({"target_lang": lang, "system": system, "term": term, "occurrences": len(h),
                                 "compliance": round(100 * sum(h) / len(h), 1)})
            pooled = [x for h in hits.values() for x in h]
            no_conduit = [x for t, h in hits.items() if t != "conduit" for x in h]
            macro.append({
                "target_lang": lang,
                "system": system,
                "terms": len(hits),
                "occurrences": len(pooled),
                "pooled": round(100 * sum(pooled) / len(pooled), 1),
                "macro": round(sum(100 * sum(h) / len(h) for h in hits.values()) / len(hits), 1),
                "pooled_without_conduit": round(100 * sum(no_conduit) / len(no_conduit), 1),
                "occurrences_without_conduit": len(no_conduit),
            })

    wrong = []
    for lang in LANGS:
        drafts = [r for r in read_csv(CORPUS_DIR / f"drafts_{LANG_SHORT[lang]}.csv") if r["split"] in {"train", "dev"}]
        ts = load_test_set(lang)
        for term, pattern in WRONG_SENSE.items():
            rx = re.compile(pattern)
            with_term = [r for r in drafts if term in r["glossary_terms"].split(";")]
            if with_term:
                k = sum(bool(rx.search(r["target_sentence"])) for r in with_term)
                wrong.append({"target_lang": lang, "source": "teacher_drafts_train_dev", "term": term,
                              "sentences": len(with_term), "wrong_sense": k, "pct": round(100 * k / len(with_term), 1)})
            test_ids = [sid for sid, terms in zip(ts.ids, ts.glossary_terms) if term in terms]
            for system in systems:
                if test_ids:
                    k = sum(bool(rx.search(preds[(lang, sid)].get(system, ""))) for sid in test_ids)
                    wrong.append({"target_lang": lang, "source": system, "term": term, "sentences": len(test_ids),
                                  "wrong_sense": k, "pct": round(100 * k / len(test_ids), 1)})

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in [("term_breakdown.csv", per_term), ("term_compliance_macro.csv", macro), ("wrong_sense.csv", wrong)]:
        with (args.output_dir / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {args.output_dir / name} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
