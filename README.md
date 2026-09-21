# Vocational Content Localization Engine

Research scaffold for fine-tuning IndicTrans2 on vocational/electrician-domain
English-to-Indic translation. The primary demonstrated pair is English to Hindi
(`eng_Latn` -> `hin_Deva`), with Konkani, Maithili, and Dogri left as stretch
targets.

The repository is designed to support an IEEE-format paper:

- baseline IndicTrans2 inference and evaluation,
- electrician-domain corpus construction,
- lightweight fine-tuning artifact preparation,
- baseline vs domain comparison,
- a small FastAPI integration endpoint,
- methodology and results notes.

## Current Status

The local project is runnable without a downloaded model. If the IndicTrans2
dependencies or gated Hugging Face model are unavailable, scripts use a clearly
marked glossary fallback so the pipeline can be smoke-tested end to end. This
fallback is not a research result and must not be reported as IndicTrans2 model
quality.

Generated local artifacts:

- `data/corpus/electrician_en_hi_train.csv`
- `data/corpus/electrician_en_hi_test.csv`
- `results/baseline_scores.csv`
- `results/comparison_scores.csv`
- `results/qualitative_examples.csv`
- `models/finetuned_hin_Deva/training_metadata.json`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The default model path is:

```text
ai4bharat/indictrans2-en-indic-dist-200M
```

You may need to accept the model conditions on Hugging Face before downloads
work locally.

## Phase Commands

Phase 1, inference:

```bash
python3 baseline_inference.py \
  --text "Check the insulation resistance with a megger." \
  --target-lang hin_Deva
```

For an offline smoke test:

```bash
python3 baseline_inference.py \
  --text "Check the insulation resistance with a megger." \
  --target-lang hin_Deva \
  --force-fallback
```

Phase 2, baseline evaluation:

```bash
python3 run_baseline_eval.py
```

Until the official IN22 files are placed under `data/in22`, use:

```bash
python3 run_baseline_eval.py --allow-sample-fallback --force-fallback
```

Phase 3, corpus construction:

```bash
python3 extract_terms.py --lang hin_Deva --rows 240
```

Add official PMKVY/NCVET/ITI text material to `data/raw/` and run:

```bash
python3 extract_terms.py --from-raw --lang hin_Deva --rows 240
```

Phase 4, fine-tuning artifact preparation:

```bash
python3 finetune.py --prepare-only
```

Phase 5, comparative evaluation:

```bash
python3 run_domain_eval.py
```

Phase 6, API:

```bash
uvicorn api.main:app --reload
```

Then open `http://127.0.0.1:8000/docs`.

## Project Layout

```text
.
├── api/
├── data/
│   ├── raw/
│   └── corpus/
├── docs/
├── localization_engine/
├── models/
├── results/
├── baseline_inference.py
├── extract_terms.py
├── finetune.py
├── run_baseline_eval.py
├── run_domain_eval.py
└── requirements.txt
```

## Research Notes

Every generated seed row is marked `needs_manual_review=True`. Replace or
validate these rows against official bilingual training material before treating
the corpus as a publishable dataset.

For paper-grade fine-tuning, use the official IndicTrans2 repository scripts and
the exported parallel files under `models/finetuned_hin_Deva/`.
# translate
