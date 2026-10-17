#!/usr/bin/env python3
"""Step 4 (GPU): domain test-set evaluation.

Systems (optionally with a terminology suffix applied to every glossary term in the source:
"+ph" = placeholder injection, the term is copied in via an entity placeholder;
"+cd" = Hugging Face lexically constrained decoding;
"+hy" = hybrid: placeholders only for sentences whose output misses a glossary term; e.g. "lora_formal+hy"):
  base         - IndicTrans2 en-indic dist-200M, untouched
  lora         - + LoRA adapter distilled on the raw teacher drafts (run 4, v1-raw-distillation)
  lora_formal  - + LoRA adapter distilled on terminology-repaired drafts (experiment 2)
  teacher      - IndicTrans2 en-indic 1B (also produced the training drafts)

References come from the human post-edited sheets when complete; otherwise the
teacher drafts are used and every output row is marked ``teacher_draft_UNVERIFIED``
(those numbers are for pipeline debugging only, not for the paper).

    python -m backend.run_domain_eval --systems base,lora,lora+cd --tag run5
    python -m backend.run_domain_eval --from-predictions a.csv b.csv --tag run5   # CPU re-scoring
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from backend.localization_engine import Translator
from backend.localization_engine.data import load_test_set
from backend.localization_engine.glossary import ACTIVE_REGISTER, ELECTRICIAN_GLOSSARIES, constraint_forms
from backend.localization_engine.languages import DEFAULT_MODEL_NAME, DOMAIN_LANGS, TEACHER_MODEL_NAME
from backend.localization_engine.metrics import paired_bootstrap, score_corpus, term_accuracy, term_compliance
from backend.localization_engine.paths import MODELS_DIR, RESULTS_DIR
from backend.localization_engine.terminology import translate_with_term_fallback


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate translation systems on the domain test sets.")
    p.add_argument("--langs", default=",".join(DOMAIN_LANGS))
    p.add_argument("--systems", default="base,lora,teacher")
    p.add_argument("--adapter", type=Path, default=MODELS_DIR / "it2_lora_joint", help="Adapter for 'lora'.")
    p.add_argument("--adapter-formal", type=Path, default=MODELS_DIR / "it2_lora_joint_formal", help="Adapter for 'lora_formal'.")
    p.add_argument("--require-human-refs", action="store_true", help="Fail instead of using teacher drafts.")
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--num-examples", type=int, default=8)
    p.add_argument("--tag", default="", help="Suffix for output files, e.g. run5 (keeps earlier results).")
    p.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    p.add_argument(
        "--from-predictions",
        type=Path,
        nargs="+",
        default=None,
        help="Re-score saved domain_predictions_*.csv files (systems are merged); no GPU needed.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    langs = args.langs.split(",")
    model_for = {
        "base": DEFAULT_MODEL_NAME,
        "lora": str(args.adapter),
        "lora_formal": str(args.adapter_formal),
        "teacher": TEACHER_MODEL_NAME,
    }

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
            base_name, guidance = split_system(system)
            row = {
                "target_lang": lang,
                "system": system,
                "model": model_for.get(base_name, base_name),
                "term_guidance": guidance or "none",
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
            # Significance of every system against the untouched base model.
            if system != "base" and "base" in systems:
                row.update(paired_bootstrap(predictions["base"][lang], preds, ts.references))
            score_rows.append(row)
            print(
                f"{lang} {system:16s} BLEU {scores.bleu:6.2f}  chrF++ {scores.chrf_pp:6.2f}  "
                f"term-acc {term_acc} (n={term_n})  compliance[{ACTIVE_REGISTER}] {compliance} (n={compliance_n})"
            )

        for i in range(len(ts.ids)):
            record = {"target_lang": lang, "id": ts.ids[i], "english_sentence": ts.sources[i], "reference": ts.references[i]}
            record.update({f"{s}_prediction": predictions[s][lang][i] for s in systems})
            all_rows.append(record)
            if i < args.num_examples:
                example_rows.append(record)

    ref_tag = "human" if all(ts.reference_type == "human_post_edited" for ts in test_sets.values()) else "UNVERIFIED"
    suffix = f"{ref_tag}_{args.tag}" if args.tag else ref_tag
    write_csv(args.output_dir / f"domain_scores_{suffix}.csv", score_rows)
    write_csv(args.output_dir / f"domain_predictions_{suffix}.csv", all_rows)
    write_csv(args.output_dir / f"qualitative_examples_{suffix}.csv", example_rows)
    print(f"\nWrote results to {args.output_dir} (*_{suffix}.csv)")


def generate_predictions(systems: list[str], model_for: dict[str, str], test_sets: dict, batch_size: int) -> dict:
    """One model in memory at a time; the plain, +ph and +cd variants of a model share it."""
    predictions: dict[str, dict[str, list[str]]] = {s: {} for s in systems}
    by_model: dict[str, list[str]] = {}
    for system in systems:
        by_model.setdefault(split_system(system)[0], []).append(system)
    for name, variants in by_model.items():
        if name not in model_for:
            raise ValueError(f"Unknown system '{name}'. Known: {sorted(model_for)} (optionally with +ph / +cd / +hy).")
        translator = Translator(model_for[name], allow_fallback=False)
        for system in variants:
            for lang, ts in test_sets.items():
                guidance = split_system(system)[1]
                kwargs = {}
                if guidance == "cd":
                    kwargs["constraints"] = [[constraint_forms(t, lang) for t in terms if constraint_forms(t, lang)]
                                             for terms in ts.glossary_terms]
                elif guidance == "ph":
                    glossary = ELECTRICIAN_GLOSSARIES[lang]
                    kwargs["term_placeholders"] = [[(t, glossary[t]) for t in terms if t in glossary]
                                                   for terms in ts.glossary_terms]
                if guidance == "hy":
                    predictions[system][lang], retried = translate_with_term_fallback(
                        translator, ts.sources, lang, ts.glossary_terms, batch_size=batch_size
                    )
                    print(f"  {system} {lang}: placeholder retry for {sum(retried)}/{len(retried)} sentences")
                    continue
                predictions[system][lang] = translator.translate_batch(
                    ts.sources, lang, batch_size=batch_size, show_progress=True, **kwargs
                )
        translator.unload()
        del translator
    return predictions


def split_system(system: str) -> tuple[str, str]:
    """'lora+ph' -> ('lora', 'ph'); 'base' -> ('base', '')."""
    name, _, guidance = system.partition("+")
    if guidance not in ("", "ph", "cd", "hy"):
        raise ValueError(f"Unknown terminology guidance '+{guidance}' in system '{system}'")
    return name, guidance


def load_saved_predictions(paths: list[Path], test_sets: dict) -> tuple[list[str], dict]:
    systems: list[str] = []
    predictions: dict[str, dict[str, list[str]]] = {}
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        file_systems = [c.removesuffix("_prediction") for c in rows[0] if c.endswith("_prediction")]
        by_key = {(r["target_lang"], r["id"]): r for r in rows}
        for lang, ts in test_sets.items():
            missing = [i for i in ts.ids if (lang, i) not in by_key]
            if missing:
                raise ValueError(f"{path} has no predictions for {len(missing)} {lang} test ids (e.g. {missing[:3]}).")
            for s in file_systems:
                predictions.setdefault(s, {})[lang] = [by_key[(lang, i)][f"{s}_prediction"] for i in ts.ids]
        systems += [s for s in file_systems if s not in systems]  # later files override duplicates
        print(f"Loaded predictions for {file_systems} from {path}")
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
