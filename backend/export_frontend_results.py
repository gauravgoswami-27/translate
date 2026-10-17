#!/usr/bin/env python3
"""Export experiment results + glossary into frontend/src/data/results.json (CPU only).

The frontend's Results and Glossary pages read this file, so they always show the
numbers in backend/results/ rather than hand-typed values. Re-run after every run:

    python -m backend.export_frontend_results
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from backend.localization_engine.glossary import load_glossary
from backend.localization_engine.languages import DOMAIN_LANGS, LANGUAGE_NAMES
from backend.localization_engine.paths import BACKEND_DIR, CORPUS_DIR, RESULTS_DIR

OUT = BACKEND_DIR.parent / "frontend" / "src" / "data" / "results.json"
DOMAIN_SCORES = RESULTS_DIR / "domain_scores_UNVERIFIED_run5_hy.csv"   # base/lora/lora_formal(+ph/+cd/+hy)/teacher
SYSTEM_LABELS = {
    "base": "Base 200M",
    "lora": "LoRA, raw drafts (run 4)",
    "lora_formal": "LoRA, terminology-aware (run 5)",
    "teacher": "Teacher 1B",
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def num(value: str):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def main() -> None:
    domain = [
        {
            "lang": r["target_lang"],
            "system": r["system"],
            "bleu": num(r["bleu"]),
            "chrf": num(r["chrf_pp"]),
            "termAccuracy": num(r["term_accuracy"]),
            "compliance": num(r["term_compliance"]),
            "deltaChrf": num(r.get("delta_chrf_pp_mean")),
            "pValue": num(r.get("p_value")),
            "reference": r["reference_type"],
        }
        for r in rows(DOMAIN_SCORES)
    ]

    in22 = {}
    for name, path in [("base", "in22_gen_scores.csv"), ("lora", "in22_gen_lora.csv"), ("lora_formal", "in22_gen_lora_formal.csv")]:
        p = RESULTS_DIR / path
        if p.exists():
            for r in rows(p):
                if name == "base" and r["system"] != "base":
                    continue
                in22.setdefault(r["language_code"], {"lang": r["language_code"], "name": LANGUAGE_NAMES[r["language_code"]]})
                in22[r["language_code"]][name] = num(r["chrf_pp"])
                in22[r["language_code"]][f"{name}Bleu"] = num(r["bleu"])

    repair = {}
    for p in sorted(RESULTS_DIR.glob("term_repair_stats_*_*.json")):
        repair.update(json.loads(p.read_text(encoding="utf-8")))

    corpus = {"sentences": 0, "train": 0, "dev": 0, "test": 0}
    for r in rows(CORPUS_DIR / "en_sentences.csv"):
        corpus["sentences"] += 1
        corpus[r["split"]] += 1

    primary, variants, status = load_glossary("formal")
    loan = load_glossary("loanword")[0]
    glossary = {
        lang: [
            {
                "english": t,
                "term": primary[lang][t],
                "variants": list(variants[lang][t]),
                "status": status[lang][t],
                "loanword": loan[lang][t],
            }
            for t in sorted(primary[lang])
        ]
        for lang in DOMAIN_LANGS
    }

    data = {
        "generated": date.today().isoformat(),
        "sources": {
            "domain": f"backend/results/{DOMAIN_SCORES.name}",
            "in22": "backend/results/in22_gen_*.csv",
            "repair": "backend/results/term_repair_stats_*.json",
            "glossary": "backend/data/glossary/electrician_glossary.csv",
        },
        "systemLabels": SYSTEM_LABELS,
        "domainLangs": list(DOMAIN_LANGS),
        "languageNames": LANGUAGE_NAMES,
        "corpus": corpus,
        "domain": domain,
        "in22": sorted(in22.values(), key=lambda r: -(r.get("base") or 0)),
        "repair": repair,
        "glossary": glossary,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {OUT} ({len(domain)} domain rows, {len(in22)} IN22 languages, {sum(map(len, glossary.values()))} glossary rows)")


if __name__ == "__main__":
    main()
