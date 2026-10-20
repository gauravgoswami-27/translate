# Methodology and Replication Guide

Everything needed to describe the experiments in the paper and to reproduce them exactly. Keep it in sync with the code: any change to a setting, script or run gets recorded here, with the run it applies to.

- **Companion documents:** `OBSERVATIONS.md` (results and findings), `references.bib` (citation keys in `[brackets]`).
- **Code:** branch `indictrans2-pipeline`. Run 4 corresponds to tag `v1-raw-distillation`; per-run commits are in §10.

---

## 1. Overview

```
NIMI Electrician PDFs ──► English sentences (24,636) ──► page-block split (train/dev/test)
                                   │
                    IndicTrans2-1B teacher (forward translation) ──► raw drafts (hi, gom, mai, doi)
                                   │                                       │
                                   │                         terminology repair (placeholders)
                                   │                                       │
                     Run 4: LoRA on raw drafts             Run 5: LoRA on repaired drafts
                                   └──────── IndicTrans2-dist-200M student ────────┘
                                   │
         Evaluation: domain test (200/lang, post-edited) + IN22-Gen (forgetting) + term compliance
```

**Research questions:**
- **RQ1.** Does distilling a 1B teacher into a 200M student on in-domain sentences improve domain translation, especially for low-resource languages?
- **RQ2.** Does distillation inherit the teacher's terminology errors?
- **RQ3.** Does terminology-aware distillation fix them, and how does it compare with enforcing terminology at inference time?

## 2. Languages, models and terminology register

- **Source language:** English (`eng_Latn`).
- **Target languages:**
  - Runs 4–6: Hindi (`hin_Deva`); Konkani (`gom_Deva`), Maithili (`mai_Deva`), Dogri (`doi_Deva`), all in Devanagari.
  - **Added in run 7:** Marathi (`mar_Deva`), Gujarati (`guj_Gujr`), Tamil (`tam_Taml`), Telugu (`tel_Telu`), Kannada (`kan_Knda`): four scripts, including three Dravidian (agglutinative) languages.
  - Since run 7, scripts default to all 9 languages, so reproducing runs 4–6 needs `--langs hin_Deva,gom_Deva,mai_Deva,doi_Deva`. Language codes follow IndicTrans2 / FLORES conventions `[gala2023indictrans2]`.
- **Teacher:** `ai4bharat/indictrans2-en-indic-1B` (Hugging Face).
- **Student / base:** `ai4bharat/indictrans2-en-indic-dist-200M`: 218,264,576 parameters including the LoRA modules; 6,488,064 trainable (2.97%).
- Both models are gated on Hugging Face (accept the terms, then use a read token).
- **Terminology register:** *formal* native/standard technical terms (NCERT/CSTT style `[ncert_science10]` `[cstt]`). Loanwords are kept only where no established native term is in use. See §5.

## 3. Data

### 3.1 Source documents
- 9 PDFs published by NIMI for DGT / MSDE `[nimi_electrician]`: Electrician CITS Trade Theory Vol. 1, CITS Trade Practical, CITS question paper, and CTS Trade Theory semesters 1–4 and Trade Practical semesters 2 and 4.
- The exact URLs are in `backend/fetch_real_materials.py`; downloaded October 2026.
- **Licence:** the CITS books are marked "NOT TO BE REPUBLISHED", so extracted text isn't redistributed publicly (see §11).

### 3.2 Sentence extraction (`backend/build_corpus.py`)
1. **Text extraction:** PyMuPDF `[pymupdf]` `page.get_text("text")`, one page at a time. pypdf was rejected because it split words across lines.
2. **Header and footer removal:** lines occurring on ≥ max(3, 5% of pages) pages in a document are dropped.
3. **Segmentation:**
   - wrapped lines are joined; hyphenated line breaks are merged
   - bullets, numbered items and `TASK/Rule/Step/Note` lines start new segments
   - a short (≤ 6 words), capitalised, unpunctuated line at the start of a segment is treated as a heading
4. **Sentence splitting:** regex at `[.!?]` followed by whitespace and an uppercase letter or quote. Common abbreviations (e.g., i.e., No., Fig., …) are protected.
5. **Cleaning:** list markers stripped, whitespace and punctuation spacing normalised.
6. **Filters** (a sentence is kept only if it passes all of them):
   - 5–45 words
   - letters ≥ 60% of non-space characters
   - uppercase ≤ 50% of letters
   - digits ≤ 20% of characters
   - no URL, e-mail or boilerplate (copyright, NIMI, "printed in")
   - starts with a capital letter, digit or quote, and ends with `.`, `!` or `?`
7. **Deduplication:** on a normalised key (lowercase, alphanumerics only).
8. **Term tagging:** English glossary terms (32, §5) plus 60 extra domain terms (`EXTRA_DOMAIN_TERMS`), matched case-insensitively with an optional plural "s".

Result: **24,636 sentences.**

### 3.3 Train / dev / test split
- **Unit:** blocks of 10 consecutive pages per document (`--block-pages 10`), shuffled with seed 13.
- **Test:** whole blocks are taken until the pool holds ≥ 400 sentences. From the pool, 200 test sentences are chosen, 75% of them containing domain terms (150/200); the other pool sentences are discarded, never moved to train.
- **Dev:** the next blocks, until ≥ 300 sentences (354).
- **Train:** everything else (24,082).
- **Leakage control:** train sentences whose 4-gram Jaccard similarity to any dev/test sentence is ≥ 0.7 are removed (3 removed).

### 3.4 Teacher drafts: forward translation (`backend/generate_drafts.py`)
- **Model:** the teacher translates *all* sentences (train, dev and test) into each target language.
- **Preprocessing:** IndicTransToolkit `IndicProcessor` `[indictranstoolkit]` (normalisation, language tags, entity placeholders).
- **Decoding:**
  - beam size 5
  - max_length = min(256, 2 × source tokens + 16)
  - fp16 on GPU
  - length-sorted batches capped at 64 sentences and a token budget of sentences × source tokens × beams ≤ 8,000, halved on CUDA out-of-memory
- **Hardware and speed:** 2 × T4 (two languages per GPU), 13–14 sentences/s per GPU, about 30 min per language.
- **Draft statistics:** in `OBSERVATIONS.md` §3.
- **Test drafts** are the seeds for human post-editing (§7.1) and are never used for training.

## 4. Training data variants

| Variant | File | Used in |
|---|---|---|
| raw | `drafts_<lang>.csv` | run 4 |
| formal (repaired) | `drafts_<lang>_formal.csv` (`term_repair` ∈ kept / repaired / failed; failed rows excluded) | run 5, run 6 |

### 4.1 Terminology repair (`backend/repair_drafts.py`, run 5)
- **Selection:** train/dev drafts whose source contains glossary terms but whose draft lacks an accepted formal form for at least one of them (matched after normalisation, §7.3). Per language: hi 3,557, gom 3,869, mai 3,476, doi 3,725.
- **Method, placeholder injection** (default, `--method placeholder`):
  1. After `IndicProcessor.preprocess`, each English glossary term (optionally plural) is replaced by `< IDn >`, numbered after the toolkit's own placeholders.
  2. The teacher translates (beam 5).
  3. Placeholders are restored to the formal glossary term. Bracket variants and Devanagari spellings of "ID" are tolerated. A space is added before the term only if it would otherwise fuse with the previous word.
  4. **[run 6]** Detached case endings after the term are re-attached: Maithili क/केँ/कें/सँ/सं/मे; Konkani च्या/ची/चो/चें/चे/चेर/क (§4.2).
- **Validation:** a repair is rejected if
  - a glossary term is still missing, or
  - a term appears only after the final sentence punctuation, or
  - the word-length ratio to the original draft is outside 0.7–1.5.
- **Outcome:** 98.7% repaired in every language; about 7 min per language on one T4. Failure reasons are stored in `results/term_repair_stats_*.json`.
- **Alternative tried and rejected:** Hugging Face lexically constrained beam search (`force_words_ids`) `[hokamp2017lexically]` `[post2018fast]`:
  - disjunctive constraints over the term and its variants
  - token-prefix-redundant alternatives pruned
  - only 5/20 usable on the smoke test (terms tacked on after the sentence), at ~1.5 s per sentence

### 4.2 Case-ending correction (post-hoc, applies to run 6)
- **Problem:** placeholder repair led the teacher to write attached case endings as separate words.
- **Correction:** `attach_case_suffixes` was applied to the repaired rows of the existing formal drafts: 1,050 Maithili and 427 Konkani rows changed (`results/suffix_fix_stats.json`).
- **Not affected:** Hindi and Dogri, where postpositions are separate words.
- **Run-7 languages:** Gujarati and Marathi get attach lists (Gujarati joins cleanly; Marathi misses the oblique vowel). Tamil, Telugu and Kannada are deliberately left alone, because their suffixes join with sandhi, which rule-based joining would get wrong. `analyze_case_endings.py` measures detached suffixes there with probe lists. For them, "attached" counts any well-formed (inflected or bare) occurrence of the term or its stem.

## 5. Glossary

- **File:** `backend/data/glossary/electrician_glossary.csv`: 32 English terms × 4 languages × 2 registers.
- **Columns:** `english_term, target_lang, register, term, variants (|-separated), status, note`.
- **Registers:**
  - `formal`: active, selected by `LE_TERM_REGISTER`
  - `loanword`: the v1 glossary, kept for comparison
- **Status:**
  - `standard`: established NCERT/CSTT usage (11 Hindi entries)
  - `proposed`: needs expert review (all non-loanword Konkani, Maithili and Dogri entries; 16 Hindi entries)
  - `loanword_kept`: no native term in use (cable, fuse, megger, main switch, terminal block)
- **Variants** are spelling or form alternatives of the *same* term only. Wrong-sense renderings (चरण for phase, पृथ्वी for earthing) are never listed.
- **Review: not done (project decision, 2026-10-20).** There was no native-speaker review. `proposed` entries are used as final, so the glossary is author-curated: NCERT/CSTT-based for Hindi, and by analogy for Konkani, Maithili and Dogri. State this as a limitation; all terminology metrics measure adherence to *this* glossary.

## 6. Student fine-tuning (`backend/finetune.py`)

| Setting | Value |
|---|---|
| Base model | indictrans2-en-indic-dist-200M, attention `eager` |
| Method | LoRA `[hu2022lora]` via PEFT `[peft]` |
| LoRA rank / alpha / dropout | 16 / 32 / 0.1 |
| LoRA target modules | q_proj, k_proj, v_proj, out_proj, fc1, fc2 (encoder and decoder) |
| Trainable parameters | 6,488,064 / 218,264,576 (2.97%) |
| Training data | joint multilingual: all 4 languages mixed and shuffled (seed 42) |
| Preprocessing | `IndicProcessor(inference=False)`: source with `eng_Latn <tgt>` tags, target `is_target=True` |
| Tokenisation | source ≤ 256 tokens (truncated); targets not truncated, pairs dropped instead if target > 160 tokens or > 3× source |
| Collator | left-padded sources, labels right-padded with −100, pad to a multiple of 8 (reimplemented: IndicTransToolkit 1.1.1's collator is broken) |
| Batch | 16 per device × gradient accumulation 4 = 64 |
| Optimiser | AdamW, lr 3e-4, β₂ = 0.98, weight decay 0.01, max grad norm 1.0 |
| Schedule | inverse square root, 300 warm-up steps |
| Label smoothing | 0.1 (`model.set_label_smoothing`) |
| Precision | fp16 mixed precision |
| Epochs | 3 (max 4,515 steps); early stopping patience 4 evaluations |
| Model selection | dev chrF++ every 500 steps, beam 4, 200 dev sentences per language (800 total), best checkpoint restored |
| Saved artefact | LoRA adapter only (~26 MB); merged into the base for inference |
| Seed | 42 (single seed so far) |

Per-run training facts:

| Run | Data | Train pairs | Length-filter drops (hi/gom/mai/doi) | Best step | Best dev chrF++ | Time |
|---|---|---|---|---|---|---|
| 4 | raw | 96,248 | 15 / 31 / 15 / 19 | 4,000 | 82.70 (vs raw drafts) | 111 min |
| 5 | formal | 96,074 | 13 / 24 / 13 / 14 | 4,500 | 82.14 (vs repaired drafts) | 117 min |
| 6 | formal + case fix, seed 42 (main) | 96,074 | 13 / 24 / 13 / 14 | 4,500 | 82.33 (vs repaired drafts) | 123 min |
| 6 | formal + case fix, seed 43 | 96,074 | same | 3,000 | 81.97 | 122 min |
| 6 | formal + case fix, Hindi only (`--langs hin_Deva`) | 24,009 | 13 | 1,000 | 87.85 (Hindi dev only) | 25 min |

The dev chrF++ values are measured against different references (raw vs repaired drafts), so they're not comparable across runs.

## 7. Evaluation

### 7.1 Domain test set and references
- 200 sentences per language (§3.3).
- **References:** teacher drafts **post-edited by fluent speakers** following `backend/data/corpus_v2/POSTEDIT_GUIDE.md`:
  - formal register; glossary terms required
  - free rewriting encouraged, to reduce post-editing bias `[toral2019post]`
  - every sentence filled
  - editor and time recorded
- Test drafts are never terminology-repaired, so the references aren't biased toward run 5/6.
- **Until post-editing is complete,** scores use raw teacher drafts and are tagged `UNVERIFIED`. They aren't for the paper. Teacher scores against its own drafts are meaningless (~99.9).
- **Record here when done:** editors per language (anonymised), editing time, number of SKIP rows.

### 7.2 Systems compared
- `base`, `lora` (run 4), `lora_formal` (run 5), `teacher`; any further adapter as `lora_<run>`, e.g. `lora_joint_formal_v2` (run 6).
- Each can be combined with an inference-time terminology mode:
  - `+ph`: placeholder injection for every glossary term in the source
  - `+cd`: Hugging Face constrained decoding
  - `+hy` (hybrid): normal decoding; placeholder retry only for sentences whose output misses a glossary term; retry kept if it reduces missing terms; then case-ending re-attachment
- **Decoding** for every system: beam 5, the token-budgeted batching of §3.4; fp16 on GPU, fp32 on CPU.

### 7.3 Metrics (`backend/localization_engine/metrics.py`)
- **BLEU** `[papineni2002bleu]` and **chrF++** `[popovic2017chrf]` (character order 6, word order 2, β = 2) with sacreBLEU `[post2018call]`, default 13a tokenisation, corpus level. sacreBLEU 2.4.3 on Kaggle, 2.6.0 locally; scores are identical for these metrics.
- **Spelling normalisation, used for term matching only** (since run 7, applied per Unicode Indic block in all scripts except Tamil, plus removal of ZWJ/ZWNJ):
  - NFC
  - nukta removed
  - chandrabindu → anusvara
  - half-nasal before a consonant (ङ्/ञ्/ण्/न्/म्) → anusvara
  - hyphens → space
- **Stem matching (run-7 languages only):** Marathi, Gujarati, Tamil, Telugu and Kannada inflect nouns by changing the stem ending (மின்னழுத்தம் → மின்னழுத்தத்தை). For them, the term with its final inflectable ending removed (last word, stem of at least 4 characters) is also accepted. Runs 4–6 languages are unaffected.
- **Term accuracy:** among (sentence, term) pairs where the *reference* contains an accepted form of the glossary term, the share where the output also does.
- **Term compliance** (reference-free): among all glossary-term occurrences in the *source*, the share where the output contains an accepted form. Primary terminology metric.
- **Significance:** paired bootstrap resampling `[koehn2004statistical]` on chrF++. 1,000 resamples (numpy default_rng, seed 12345), every system against `base`; mean Δ, 95% percentile interval, p = share of resamples with Δ ≤ 0. Sentence-level sacreBLEU statistics are summed per resample.
- **Re-scoring without a GPU:** `run_domain_eval.py --from-predictions <files…> --tag <tag>` re-scores saved predictions against the current references (e.g. after post-editing).

### 7.4 General-domain benchmark and forgetting
- **IN22-Gen** `[gala2023indictrans2]` (`ai4bharat/IN22-Gen`, test split, 1,024 sentences, gated): English → all 22 scheduled languages for `base` (Table 1); English → the 4 domain languages for each adapter (forgetting check). Sindhi uses `snd_Deva`, as in IN22.
- Same decoding and metrics as §7.3.
- These BLEU values aren't directly comparable to AI4Bharat's (different tokenisation); compare chrF++.

### 7.5 Terminology analysis (`backend/analyze_terminology.py`)
For each term and language: the share of train/dev drafts containing the English term whose draft uses an accepted glossary form (normalised), plus the most frequent words in the misses. Run for both registers.

## 8. Software and hardware

| | Kaggle (training, evaluation) | Local (API, CPU evaluation) |
|---|---|---|
| Hardware | 2 × NVIDIA T4 16 GB (training on one GPU; the second ran evaluations in parallel) | Intel i7 laptop, 16 cores, 15 GB RAM; RTX 3050 present but driver not loaded, so CPU |
| Python | 3.13.15 | 3.12 (`backend/.venv-api`) |
| torch | 2.11.0+cu128 (Kaggle image) | 2.5.1+cpu |
| transformers | 4.46.3 (pinned: IndicTrans2's remote code uses the legacy tuple KV cache) | 4.46.3 |
| peft / accelerate | 0.13.2 / 1.1.1 | 0.13.2 / 1.1.1 |
| IndicTransToolkit | 1.1.1 | 1.1.1 |
| sacrebleu | 2.4.3 | 2.4.3 (API env) |
| datasets / hf-hub | ≥ 2.20, < 4 / < 1.0 | (hf-hub < 1.0) |
| PDF extraction | PyMuPDF 1.28.2 (local, Python 3.14 env) | |

Pinned requirements: `kaggle/requirements-kaggle.txt`, `backend/requirements-api.txt`.

## 9. How to reproduce

```bash
# --- local, CPU (repository root) ---
python -m backend.fetch_real_materials          # 9 PDFs -> backend/data/raw/
python -m backend.build_corpus                  # -> backend/data/corpus_v2/en_sentences.csv (24,636 rows)
bash kaggle/make_bundle.sh                      # -> kaggle/dist/vocational-nmt-bundle.zip (private Kaggle dataset)

# --- Kaggle, 2xT4: notebooks do the following ---
python -m backend.generate_drafts --langs hin_Deva,mai_Deva        # GPU 0   (run 4 notebook)
python -m backend.generate_drafts --langs gom_Deva,doi_Deva        # GPU 1
python -m backend.finetune --run-name joint                        # run 4
python -m backend.repair_drafts --langs hin_Deva,mai_Deva          # run 5 notebook (GPU 0 / GPU 1 split)
python -m backend.finetune --drafts-variant formal --run-name joint_formal
python -m backend.run_domain_eval --systems base,base+ph,base+cd,lora,lora+ph,lora+cd,teacher --tag run5a
python -m backend.run_domain_eval --systems lora_formal,lora_formal+ph,lora_formal+cd --tag run5b
python -m backend.run_domain_eval --from-predictions backend/results/domain_predictions_UNVERIFIED_run5{a,b}.csv --tag run5
python -m backend.run_baseline_eval --output backend/results/in22_gen_scores.csv            # Table 1
python -m backend.run_baseline_eval --skip-base --adapter backend/models/it2_lora_joint_formal \
       --output backend/results/in22_gen_lora_formal.csv                                     # forgetting

# --- local, CPU ---
backend/.venv-api/bin/python -m backend.run_domain_eval --systems lora_formal+hy --tag local_hy
python -m backend.analyze_terminology
# after post-editing (final paper numbers):
python -m backend.run_domain_eval --from-predictions <prediction files> --require-human-refs --tag final
```
Notebooks: `kaggle/run4_raw_distillation.ipynb`, `kaggle/run5_terminology_aware.ipynb`, `kaggle/run6_case_fixed.ipynb`. Each run uses a stamped bundle (`kaggle/BUNDLE_VERSION`), recorded in §10.

## 10. Run registry

| Run | Date | Code (commit / bundle stamp) | What | Outputs |
|---|---|---|---|---|
| 4 | 2026-10-15 | ≈ `bc3a66b` (tag `v1-raw-distillation`), bundle `20261015T095502Z` | drafts, joint LoRA on raw drafts, domain eval (base/lora/teacher), IN22-Gen 22 languages + forgetting | `models/it2_lora_joint`, `results/*_run4.csv`, `results/in22_gen_*.csv`; archive `kaggle/runs/2026-10-15_run4/` |
| 5 | 2026-10-15/16 | `0f0f7dc`, bundle `20261015T143013Z` | placeholder repair, joint LoRA on repaired drafts, 10-system eval, forgetting | `models/it2_lora_joint_formal`, `results/*_run5*.csv`, `term_repair_stats_*.json`, `in22_gen_lora_formal.csv`; archive `kaggle/runs/2026-10-15_run5/` |
| local-hy | 2026-10-17 | `359a04e` (CPU, `.venv-api`) | hybrid terminology evaluation of the run-5 model | `results/*_local_hy.csv`, `*_run5_hy.csv` |
| 8 | pending | bundle `20261020T092712Z` | `joint_formal_v2_s44` (third seed of the main model); Hindi-only LoRA rank sweep r = 4, 8, 32, 64 (alpha = 2r) | notebook `kaggle/run8_seed_rank.ipynb` (generator `kaggle/build_run8_notebook.py`); seed 44 uses the original 4 languages explicitly |
| 7 | pending | bundle `20261020T092712Z` | 5 new languages: teacher drafts + placeholder repair; `joint9_formal` (all 9 languages) and `new5_formal` (new 5), 2 epochs, eval-steps 1,000, 100 dev/language; evaluation of base/teacher/both models (+hy); IN22-Gen forgetting for joint-9 | notebook `kaggle/run7_new_languages.ipynb` (generator `kaggle/build_run7_notebook.py`) |
| 6 | 2026-10-17 | `c88d42f`, bundle `20261017T103217Z` | `joint_formal_v2` (seed 42, main model) on case-fixed drafts; `joint_formal_v2_s43` (seed variance); `hi_formal_v2` (Hindi-only ablation); eval plain + `+hy`; IN22-Gen forgetting for v2. Merged scoring locally: tags `run6_all`, `run6_hi`; case endings: `analyze_case_endings.py` | `models/it2_lora_{joint_formal_v2,joint_formal_v2_s43,hi_formal_v2}`, `results/*_run6*.csv`, `in22_gen_lora_formal_v2.csv`, `case_endings.csv`; archive `kaggle/runs/2026-10-17_run6/` |

Failed or aborted Kaggle attempts (environment and bug fixes, no results) are logged in `PROGRESS.md`. They don't affect the reported numbers.

## 11. Ethics, licensing and data availability (to finalise)
See `DATA_SOURCES.md` for every source, its licence, and the compute ledger.
- **Source texts:** government training material; CITS books marked "NOT TO BE REPUBLISHED". We release code, glossary, model adapters and scores. The corpus is offered on request for research, or as sentence IDs plus extraction scripts. **Decide before submission.**
- **Models:** IndicTrans2 licence (verify; believed MIT), and the IN22 licence is CC-BY-4.0.
- **Post-editors:** consent, compensation and acknowledgement. Record here.

## 12. Known deviations and caveats to report
- Two seeds (42, 43) for the main run-6 configuration only; other configurations have a single seed. Measured seed variance: up to ~1 chrF++.
- The domain test set is small (200 per language) and its references are post-edited, not translated from scratch.
- Training targets are machine-generated (distillation), not human translations.
- The glossary wasn't reviewed by native speakers (all languages). Konkani, Maithili and Dogri entries are by analogy with the Hindi NCERT/CSTT register.
- Placeholder insertion can't inflect the term; case endings are re-attached by rule (Maithili, Konkani), but the Konkani oblique stem vowel isn't restored.
- Dev chrF++ used for model selection is measured against teacher drafts (raw or repaired), not human references.
