# Build Brief: Vocational Content Localization Engine
### (Paste this into Antigravity / Claude Code / any agentic coding tool)

---

## Project Overview

Build a research project that fine-tunes **IndicTrans2** (AI4Bharat's open-source translation model, covering all 22 scheduled Indian languages) on a **custom vocational/electrician-domain corpus**, to demonstrate improved technical terminology translation accuracy for English→Hindi (and optionally 2-3 additional low-resource Indian languages: Konkani, Maithili, Dogri).

The final output must include: working code, a domain dataset, evaluation results (baseline vs fine-tuned), a simple REST API, and documentation — structured to directly support an IEEE-format research paper.

---

## Tech Stack

- Python 3.10+
- IndicTrans2 (github.com/AI4Bharat/IndicTrans2)
- Hugging Face `transformers`, `sentencepiece`
- BPCC (Bharat Parallel Corpus Collection) — for baseline reference only
- FastAPI — for the API layer
- `sacrebleu` — for BLEU/chrF scoring
- pandas — for corpus/dataset handling

---

## Phase 1 — Environment Setup

**Tasks:**
1. Clone IndicTrans2 repo, install dependencies per their README
2. Download pretrained IndicTrans2 checkpoint (en-indic, distilled/base model — pick the smaller variant given local compute constraints)
3. Write a `baseline_inference.py` script that:
   - Loads the pretrained model
   - Accepts English input text
   - Outputs translation to a specified target language (parameterized, not hardcoded to Hindi)
4. Test on 5-10 sample sentences per target language to confirm setup works end-to-end

**Deliverable:** Working inference pipeline, confirmed functional.

---

## Phase 2 — Baseline Evaluation (All 22 Languages)

**Tasks:**
1. Download the IN22 benchmark test set (AI4Bharat's official evaluation set)
2. Write `run_baseline_eval.py` that:
   - Loops through all 22 languages
   - Runs IndicTrans2 (untouched) on IN22 test sentences
   - Computes BLEU and chrF per language using `sacrebleu`
   - Outputs results to `results/baseline_scores.csv`
3. Generate a simple bar chart or table visualizing baseline scores across all 22 languages

**Deliverable:** `results/baseline_scores.csv` + visualization — this becomes Table 1 in the paper.

---

## Phase 3 — Domain Corpus Construction

**Tasks:**
1. Create `data/raw/` folder for source materials
2. Write a scraper/parser script (`extract_terms.py`) to pull technical vocabulary from:
   - PMKVY electrician qualification pack PDFs (search & download from PMKVY/NCVET portals)
   - Any available bilingual ITI training material
3. Structure the output as `data/corpus/electrician_en_hi.csv` with columns:
   `id, english_term, hindi_term, english_sentence, hindi_sentence, source`
4. Target: 200-500 rows. Where bilingual source material is unavailable, generate a draft translation using the baseline model, then flag it as `needs_manual_review = True` for manual correction
5. Repeat for 2-3 additional low-resource languages (Konkani, Maithili, Dogri) if time permits — same structure, separate CSVs
6. Split each language's corpus into `train.csv` (80%) and `test.csv` (20%)

**Deliverable:** `data/corpus/` folder with per-language train/test CSVs — this is the original dataset artifact for the paper.

---

## Phase 4 — Fine-Tuning

**Tasks:**
1. Convert corpus CSVs into the format IndicTrans2's fine-tuning scripts expect (see their `prepare_data_joint_finetuning.sh`)
2. Write `finetune.py` (or adapt IndicTrans2's provided fine-tuning script) to:
   - Load the pretrained checkpoint
   - Fine-tune on `train.csv` for each language
   - Save fine-tuned checkpoints to `models/finetuned_<lang>/`
3. Keep fine-tuning runs short/lightweight given likely local compute limits (few epochs, small batch size) — document actual compute used (GPU/CPU, time taken) for the paper's reproducibility section

**Deliverable:** Fine-tuned model checkpoint(s), one per target language.

---

## Phase 5 — Comparative Evaluation

**Tasks:**
1. Write `run_domain_eval.py` that:
   - Runs both baseline and fine-tuned models on each language's `test.csv`
   - Computes BLEU/chrF for both
   - Also does a simple term-match check: does the output contain the correct target technical term? (basic string match against `hindi_term` column)
2. Output `results/comparison_scores.csv` (baseline vs fine-tuned, per language)
3. Pull 5-10 qualitative example translations (before/after) per language for the paper's discussion section

**Deliverable:** `results/comparison_scores.csv` + qualitative examples — this is the paper's core results section.

---

## Phase 6 — API Layer

**Tasks:**
1. Build a FastAPI app (`api/main.py`) with:
   - `POST /translate` — takes `{"text": str, "target_lang": str, "domain": str}`, returns `{"translated_text": str}`
   - Route to the fine-tuned model if `domain == "electrician"` and target language has a fine-tuned checkpoint; otherwise fall back to baseline
2. Add basic error handling (unsupported language, empty input)
3. Write a short `api/README.md` explaining it's designed as an integration-ready endpoint for platforms like NCVET/MSDE/LMS systems (architecture demonstration, not a live integration)

**Deliverable:** Working local API, testable via `curl` or Swagger UI (`/docs`).

---

## Phase 7 — Documentation

**Tasks:**
1. `README.md` at project root — project overview, setup instructions, folder structure, how to reproduce results
2. `docs/methodology.md` — corpus construction process, fine-tuning setup, evaluation approach (this maps directly to the paper's Methodology section)
3. `docs/results.md` — results tables + qualitative examples, written up clearly (maps to paper's Results section)
4. Inline code comments/docstrings throughout

**Deliverable:** Fully documented repo, ready to write the paper from directly.

---

## Folder Structure (target)

```
localization-engine/
├── README.md
├── requirements.txt
├── baseline_inference.py
├── run_baseline_eval.py
├── extract_terms.py
├── finetune.py
├── run_domain_eval.py
├── data/
│   ├── raw/
│   └── corpus/
│       ├── electrician_en_hi_train.csv
│       ├── electrician_en_hi_test.csv
│       └── ... (other languages)
├── models/
│   └── finetuned_<lang>/
├── results/
│   ├── baseline_scores.csv
│   └── comparison_scores.csv
├── api/
│   ├── main.py
│   └── README.md
└── docs/
    ├── methodology.md
    └── results.md
```

---

## Constraints to Respect

- Scope is **English + Hindi as the primary demonstrated pair**, with Konkani/Maithili/Dogri as stretch goals if time allows — do not attempt all 22 languages for fine-tuning, only for baseline evaluation
- Keep fine-tuning lightweight — this is a proof-of-concept, not a production model
- Every dataset entry sourced from official material (PMKVY/NCVET/ITI) should retain a `source` field for citation traceability
- Flag any machine-assisted (not human-verified) corpus entries clearly — needed for honest methodology reporting in the paper
