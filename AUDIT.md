# Project Audit: Vocational NMT Localization Engine

*Audit date: 2026-10-15*

**Scope:** every code file in `backend/` and `frontend/src/`. For the data, only structure and aggregate statistics were examined. `.venv`, `node_modules` and the raw PDFs/text were not scanned.

## Bottom line

The code is a reasonable start, but **the current results can't go into a paper.** The training and test "references" aren't translations. Each one is the English sentence with only the technical term swapped into Devanagari. The fine-tuned model learned to copy English and swap one word. Its high BLEU (48–77) is a score for matching that pattern, not for translating well. On top of that, two of the four languages (Konkani, Dogri) aren't supported by the model that was used. Fix the data and the evaluation first, then train on Kaggle.

---

## P0: Critical (these make the current results invalid)

### 1. The corpus isn't parallel data
These statistics were computed over all four language CSVs:
- **98%** of target sentences contain English words, and on average **56%** of each target's characters are Latin. For example, the reference for *"Resistance of heating coil"* is `प्रतिरोध of heating coil`.
- `extract_terms.py:104-106` makes the "translation" with a regex: it replaces the English term with the glossary term inside the English sentence.
- There are only **22 unique terms** across 300 rows, and the English side is identical in all 4 languages.
- **30%** of test source sentences also appear in train, and 95% of test terms were seen in training. That is test-set leakage.
- All 300 rows are `needs_manual_review=True`, so none have been checked by a person.

### 2. Konkani and Dogri aren't supported by NLLB-200
`gom_Deva`, `doi_Deva`, `brx_Deva`, `mni_Mtei` and `sat_Olck` aren't in NLLB's vocabulary (checked against the tokenizer).
- **At inference:** `translator.py:154-157` silently skips the forced target-language token, so the baseline produces Portuguese or French. `results/qualitative_examples.csv` has the Konkani baseline output *"Resistência da bobina de aquecimento"*.
- **In training:** the target language tag became `<unk>` (id 3). This was verified.
- So the Konkani and Dogri "+66 BLEU" is mostly the gap between a model emitting the wrong language and a model that learned to copy English.
- Bodo, Manipuri and Santali all score exactly 2.5625 / 11.2345 in the 22-language table for the same reason.

### 3. Training and inference used different input formats
- `finetune.py:104` checks `tokenizer.lang_code_to_id`, which doesn't exist in transformers 4.57 (verified: `False`). So training took the **IndicTrans2 `IndicProcessor` branch** and fed IndicTrans2-style preprocessed/tagged text to NLLB.
- `translator.py` feeds raw text at inference.
- The build brief specifies **IndicTrans2**, but all of the training used NLLB.

### 4. The 22-language baseline evaluation is meaningless
- `data/in22/` was never downloaded, so every language fell back to 5 sample sentences.
- `run_baseline_eval.py:158` uses `SAMPLE_REFERENCES.get(lang, SAMPLE_EN)`, so 18 languages were scored against the **English source** as the reference.
- `--allow-sample-fallback` has `default=True` with `store_true`, so it can't be turned off.

### 5. The paper draft and docs misreport the numbers
- In `docs/results.md`, the qualitative table **swaps the columns**:
  - The text shown as "Baseline" is actually the reference.
  - The text shown as "Fine-tuned" is actually the baseline output.
  - In the CSV, the fine-tuned output is `प्रतिरोध heating coil`.
- In the paper's Table 1, the Hindi, Maithili, Konkani and Dogri rows use domain-test numbers. The CSV has different values (Hindi 49.60, not 11.24).
- Hindi **term match rate went down** after fine-tuning (75.0% → 68.3%). This is the paper's own key metric, and the draft doesn't mention it.
- The draft says "IndicTrans2 / NLLB" and "production-ready", which overclaims.
- The frontend hardcodes all of these numbers (`MetricsDashboard.jsx`, `ComparisonView.jsx`).
- When the API is offline, `frontend/src/api/client.js` labels glossary-substitution output as `models/finetuned_<lang>`.

---

## P1: Training code (`backend/finetune.py`)

| Issue | Where | Fix |
|---|---|---|
| Source and target are filtered for blanks separately, then truncated to the shorter length. One blank row shifts every pair after it out of alignment, silently. | L39-47 | Filter pairs together |
| No dev set, early stopping, LR schedule/warmup or seed. Loss of 0.07 after 5 epochs on 240 pairs means memorization. | whole loop | Use `Seq2SeqTrainer` with an eval split, `load_best_model_at_end`, `set_seed` |
| LoRA only covers `q_proj`/`v_proj` at r=8 | L93-99 | Try q,k,v,o + fc1/fc2, r=16–32, and report the ablation |
| The whole dataset is padded to a global max length | L118 | Use dynamic padding with `DataCollatorForSeq2Seq` |
| A full merged 2.4 GB checkpoint is saved per language (9.6 GB total) | L162 | Save only the LoRA adapter (~5–20 MB) |
| One model per language | design | Add a joint multilingual run; low-resource languages benefit from it, and it's a good ablation for the paper |
| Metadata is missing library versions, seed, git hash and parameter counts | L54-63 | Record them for the reproducibility section |

## P1: Evaluation (`run_domain_eval.py`, `localization_engine/metrics.py`)
- Translation runs **one sentence at a time** with beam 5. Batch it.
- `term_match_rate` is a raw substring check and counts rows that have an empty term in the denominator. It should only count terms that actually appear in the reference.
- Missing pieces a reviewer will expect:
  - **chrF++**
  - **COMET** (IndicCOMET or another COMET model that covers the target languages; check its language coverage)
  - **paired bootstrap significance** (`sacrebleu --paired-bs`)
  - **a general-domain check** on IN22-Gen or FLORES, to show fine-tuning didn't cause catastrophic forgetting
- Results are labelled `translation_backend="indictrans2"` even though the model is NLLB (`translator.py:110`).
- `translator.py:142` checks `not hasattr(self, "_processor_active")`, which is always true. The IndicTrans2 inference branch is dead code, so a real IndicTrans2 checkpoint would break.

## P2: Engineering
- **Imports and paths don't match.** The scripts import `from backend.localization_engine...`, so they have to run from the repo root. But their default paths (`data/corpus`, `models/`) are relative to `backend/`. This will break on Kaggle; use paths relative to the file or a single config.
- **Python version.** The local venv is **Python 3.14** and `requirements.txt` has no version pins. Kaggle runs 3.11/3.12, so pin `transformers`, `peft`, `sacrebleu` and `IndicTransToolkit`.
- **Empty folders.** `scripts/` and `tests/` are empty. Add at least a smoke test for data alignment and language-code support.
- **API (`backend/api/main.py`):**
  - CORS allows `*` together with `allow_credentials=True`.
  - Only one model is kept in memory, so alternating requests reload from disk every time.
  - It should validate the domain/language combination against the model's supported languages.
- **Glossary.** The glossary is hand-written with 32 terms. Cite or replace it with the **CSTT** (Commission for Scientific & Technical Terminology) electrical glossary for credibility.

---

## Recommended plan for Kaggle

**1. Fix the data first (most of the paper's value is here).**
- **Hindi.** Bharat Skills / NIMI also publish many trade books in Hindi. If the Electrician Theory and Practical books have Hindi editions, align them at sentence level (LaBSE + vecalign) to get genuine parallel data (likely 2–5k pairs).
- **Konkani, Maithili, Dogri.** Generate drafts with IndicTrans2-1B and have a person post-edit **at least the test set** (~100–200 sentences per language).
- **Splits.** Split by document or chapter, dedupe, and keep a human-verified test set.

**2. Backbone.** Switch to **IndicTrans2** `ai4bharat/indictrans2-en-indic-dist-200M` (and 1B if it fits). It covers all 22 languages, including gom, doi and brx. It's gated on Hugging Face, so put an HF token in Kaggle Secrets. Keep NLLB-600M as a second backbone, but only for Hindi and Maithili. "Two backbones × LoRA vs full fine-tuning" is a solid experiment grid.

**3. Training script.**
- Use `Seq2SeqTrainer` with PEFT and `fp16` (the T4/P100 don't support bf16).
- Hold out a dev split, use early stopping, and run 3 seeds.
- Save adapters only, to `/kaggle/working` (20 GB limit).
- Checkpoint regularly; Kaggle sessions stop at 12 hours.

**4. Evaluation.**
- Report BLEU, chrF++, COMET and term accuracy, with bootstrap confidence intervals.
- Run the real IN22-Gen benchmark (on HF `ai4bharat/IN22-Gen`) for Table 1 and the forgetting check.
- Generate every table straight from CSVs, and make the frontend read those CSVs instead of hardcoded numbers.

**5. Packaging.** Upload the corpus as a Kaggle Dataset and the code as a utility script or GitHub clone. Make one notebook that runs train → eval → export.

## Open decisions
1. Switch the backbone to IndicTrans2 (recommended), or keep NLLB?
2. How much human post-editing is possible for the test sets? This sets the scope for the low-resource languages.
