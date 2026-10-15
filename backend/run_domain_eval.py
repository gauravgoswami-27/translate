#!/usr/bin/env python3
"""Step 4 (GPU): domain test-set evaluation.

Systems:
  base     - IndicTrans2 en-indic dist-200M, untouched
  lora     - the same model + our LoRA adapter
  teacher  - IndicTrans2 en-indic 1B (upper bound; also produced the training drafts)

References come from the human post-edited sheets when complete; otherwise the
teacher drafts are used and every output row is marked ``teacher_draft_UNVERIFIED``
(those numbers are for pipeline debugging only, not for the paper).

    python -m backend.run_domain_eval --adapter models/it2_lora_joint
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from backend.localization_engine import Translator
from backend.localization_engine.data import load_test_set
from backend.localization_engine.languages import DEFAULT_MODEL_NAME, DOMAIN_LANGS, TEACHER_MODEL_NAME
from backend.localization_engine.glossary import ACTIVE_REGISTER
from backend.localization_engine.metrics import paired_bootstrap, score_corpus, term_accuracy, term_compliance
from backend.localization_engine.paths import MODELS_DIR, RESULTS_DIR


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate base vs LoRA vs teacher on the domain test sets.")
    p.add_argument("--langs", default=",".join(DOMAIN_LANGS))
    p.add_argument("--adapter", type=Path, default=MODELS_DIR / "it2_lora_joint")
    p.add_argument("--systems", default="base,lora,teacher")
    p.add_argument("--require-human-refs", action="store_true", help="Fail instead of using teacher drafts.")
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--num-examples", type=int, default=8)
    p.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    p.add_argument(
        "--from-predictions",
        type=Path,
        default=None,
        help="Re-score saved predictions (a domain_predictions_*.csv) against the current references; no GPU needed.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    langs = args.langs.split(",")
    model_for = {"base": DEFAULT_MODEL_NAME, "lora": str(args.adapter), "teacher": TEACHER_MODEL_NAME}

    test_sets = {lang: load_test_set(lang, allow_unverified=not args.require_human_refs) for lang in langs}

    if args.from_predictions:
        systems, predictions = load_saved_predictions(args.from_predictions, test_sets)
    else:
        systems = args.systems.split(",")
        predictions = generate_predictions(systems, model_for, test_sets, args.batch_size)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    score_rows, example_rows, all_rows = [], [], []
    for lang in langs:
        ts = test_sets[lang]
        for system in systems:
            preds = predictions[system][lang]
            scores = score_corpus(preds, ts.references)
            term_acc, term_n = term_accuracy(preds, ts.references, ts.glossary_terms, lang)
            compliance, compliance_n = term_compliance(preds, ts.glossary_terms, lang)
            row = {
                "target_lang": lang,
                "system": system,
                "model": model_for.get(system, system),
                "bleu": scores.bleu,
                "chrf_pp": scores.chrf_pp,
                "term_accuracy": term_acc,
                "term_occurrences": term_n,
                "term_compliance": compliance,
                "term_compliance_occurrences": compliance_n,
                "term_register": ACTIVE_REGISTER,
                "num_sentences": len(preds),
                "reference_type": ts.reference_type,
            }
            if system == "lora" and "base" in systems:
                row.update(paired_bootstrap(predictions["base"][lang], preds, ts.references))
            score_rows.append(row)
            print(f"{lang} {system:8s} BLEU {scores.bleu:6.2f}  chrF++ {scores.chrf_pp:6.2f}  term-acc {term_acc} (n={term_n})  compliance[{ACTIVE_REGISTER}] {compliance} (n={compliance_n})")

        for i in range(len(ts.ids)):
            record = {"target_lang": lang, "id": ts.ids[i], "english_sentence": ts.sources[i], "reference": ts.references[i]}
            record.update({f"{s}_prediction": predictions[s][lang][i] for s in systems})
            all_rows.append(record)
            if i < args.num_examples:
                example_rows.append(record)

    tag = "human" if all(ts.reference_type == "human_post_edited" for ts in test_sets.values()) else "UNVERIFIED"
    write_csv(args.output_dir / f"domain_scores_{tag}.csv", score_rows)
    write_csv(args.output_dir / f"domain_predictions_{tag}.csv", all_rows)
    write_csv(args.output_dir / f"qualitative_examples_{tag}.csv", example_rows)
    print(f"\nWrote results to {args.output_dir} (reference type: {tag})")


def generate_predictions(systems: list[str], model_for: dict[str, str], test_sets: dict, batch_size: int) -> dict:
    # One model in memory at a time (fits a 16 GB GPU); translate every language with it.
    predictions: dict[str, dict[str, list[str]]] = {s: {} for s in systems}
    for system in systems:
        translator = Translator(model_for[system], allow_fallback=False)
        for lang, ts in test_sets.items():
            predictions[system][lang] = translator.translate_batch(ts.sources, lang, batch_size=batch_size, show_progress=True)
        translator.unload()
        del translator
    return predictions


def load_saved_predictions(path: Path, test_sets: dict) -> tuple[list[str], dict]:
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    systems = [c.removesuffix("_prediction") for c in rows[0] if c.endswith("_prediction")]
    by_key = {(r["target_lang"], r["id"]): r for r in rows}
    predictions: dict[str, dict[str, list[str]]] = {s: {} for s in systems}
    for lang, ts in test_sets.items():
        missing = [i for i in ts.ids if (lang, i) not in by_key]
        if missing:
            raise ValueError(f"{path} has no predictions for {len(missing)} {lang} test ids (e.g. {missing[:3]}).")
        for s in systems:
            predictions[s][lang] = [by_key[(lang, i)][f"{s}_prediction"] for i in ts.ids]
    print(f"Loaded saved predictions for systems {systems} from {path}")
    return systems, predictions


def write_csv(path: Path, rows: list[dict]) -> None:
    fields: list[str] = []
    for row in rows:
        fields += [k for k in row if k not in fields]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
