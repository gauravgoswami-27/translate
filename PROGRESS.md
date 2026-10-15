# Progress Log

Short overview of what was changed and why. The full findings are in [AUDIT.md](AUDIT.md).

## 2026-10-15: Switch to IndicTrans2 and rebuild the pipeline

### Decisions
- **Backbone:** IndicTrans2 en-indic. The **dist-200M** model is the one we fine-tune (the student). The **1B** model is the teacher and the upper-bound baseline. NLLB-200 was dropped: it has no Konkani or Dogri.
- **Training data:** forward translation, also called sequence-level knowledge distillation. The 1B teacher translates real English sentences from the official textbooks, and the 200M student is fine-tuned on those translations. No official Hindi edition of the books could be found, so true parallel data wasn't an option.
- **Test data:** 200 sentences per language. Teacher drafts are **post-edited by humans**, and only those references count for the paper. Until then, every score is tagged `UNVERIFIED`.

### Done
1. **Corpus v2** (`backend/build_corpus.py`, which replaces `extract_terms.py`)
   - Downloaded 6 more NIMI Electrician books (CTS semester TT/TP), for 9 PDFs in total.
   - Switched PDF extraction from pypdf to PyMuPDF. pypdf was splitting words across lines.
   - Result: **24,636 unique English sentences**. Split: 24,082 train, 354 dev, 200 test. The split is by blocks of 10 pages, so there's no train/test leakage, and near-duplicates of test sentences are removed from train.
   - 150 of the 200 test sentences contain domain terminology.
2. **Teacher drafts** (`generate_drafts.py`): the 1B teacher translates the corpus into hi/gom/mai/doi. It also writes the post-editing sheets to `data/corpus_v2/postedit/`. It can resume after an interruption.
3. **Translator** (`localization_engine/translator.py`)
   - Rewritten for IndicTrans2: IndicProcessor, batched length-sorted decoding, and LoRA adapter loading.
   - Experiment scripts can't silently fall back to the glossary.
4. **Fine-tuning** (`finetune.py`)
   - Adapted from AI4Bharat's reference `train_lora.py`: joint multilingual LoRA (r=16) on attention and FFN layers.
   - Dev-set chrF++ selects the best checkpoint, with early stopping and a fixed seed.
   - Saves the adapter only, plus metadata (versions, GPU, timings).
5. **Evaluation**
   - `run_domain_eval.py`:
     - compares base vs LoRA vs teacher
     - reports BLEU, chrF++, and term accuracy (counted only where the reference uses the glossary term)
     - adds a paired bootstrap (95% CI and p-value)
     - saves full predictions
   - `run_baseline_eval.py`: the real IN22-Gen benchmark for all 22 languages (Table 1), plus a forgetting check for the LoRA model.
6. **Fixes:**
   - Paths no longer depend on the working directory and can be overridden by environment variables.
   - Language list aligned with IN22 (Sindhi is `snd_Deva`).
   - API routes `electrician` requests to the adapter, and CORS no longer allows `*` with credentials.
7. **Kaggle kit** (`kaggle/`): pinned requirements, `make_bundle.sh`, and `indictrans2_pipeline.ipynb`.

### Verified locally (CPU, no model weights)
- Corpus build.
- Pair alignment: a blank row drops the whole pair.
- Post-edit sheet round trip.
- Metrics, term accuracy and bootstrap.
- IndicProcessor tagging.
- API routes in fallback mode.
- Bundle build.

**Not yet run anywhere:** anything that needs the gated IndicTrans2 weights. The notebook's smoke-test cell checks this first.

### Not yet updated (don't use the old numbers)
- `backend/docs/*.md`, the paper draft, and the frontend dashboards still show the old NLLB numbers, which are invalid.
- `data/corpus/` (v1, template corpus) and `models/finetuned_*` (NLLB, 9.6 GB) are legacy and can be deleted.

### Kaggle smoke-test fixes
- **Missing output folder:** `generate_drafts.py` crashed because the output folder didn't exist. It now creates it.
- **Out of GPU memory:** the 1B teacher ran out of memory on a T4 with 48 long sentences × 5 beams.
  - `translate_batch` now batches by token budget (sentences × source tokens × beams ≤ 8000).
  - Output length is capped at 2× the source length + 16 tokens.
  - On an out-of-memory error it halves the budget and retries.
  - Retries reset IndicProcessor's placeholder queue so entities stay aligned (verified locally).
- **Speed control:** `--max-train` lets the teacher translate a subset of the training sentences if throughput is too low.

### Kaggle run 1 (2026-10-15)
- **Drafts finished:** all 4 languages × 24,636 sentences, at 13–14 sentences/s per T4, about 1 hour total on 2 GPUs.
- **Fine-tuning crashed** at step 0. IndicTransToolkit 1.1.1's `IndicDataCollator` is broken: it imports a helper inside the class body.
  - Replaced it with our own `IndicSeq2SeqCollator`, which keeps the same behaviour: left-padded sources, and labels padded with -100.
  - Unit-tested locally.
- **IN22-Gen not accessible:** access to the gated dataset hadn't been granted.
- **Notebook changes:**
  - every step now stops the run on failure
  - gated-repo access is checked up front
  - a training smoke test runs and loads its adapter before the full run
  - drafts from earlier runs are reused
  - base IN22 runs on GPU 1 during training

### Kaggle run 2
- **Draft reuse worked:** the previous run's output was attached as an input, so translation was skipped.
- **The old code ran:** that output also contains an old `project/backend/` folder, and the notebook picked it up as the code.
  - Fix: `make_bundle.sh` now writes `kaggle/BUNDLE_VERSION`.
  - The notebook only uses code folders or zips with that stamp, and takes the newest (simulated locally).

### Kaggle run 3
- **The new code ran:** the collator worked and the forward pass ran.
- **Out of GPU memory in the loss:** logits are batch × target length × ~122k vocabulary, and the first batch is the longest one (32 × ~200 tokens, a 3 GB allocation).
- **Fix:**
  - per-device batch 16 × gradient accumulation 4, keeping the effective batch at 64
  - evaluation batch 16
  - training/dev pairs are dropped when the target is over 160 tokens or more than 3× the source length; this filters degenerate teacher drafts
  - drop counts and label-length percentiles are saved in `training_metadata.json` (needed for the paper's data section)

### Kaggle run 4: first complete run (bundle 20261015T095502Z)
**Training**
- Joint LoRA (r=16) on 96,248 pairs; the length filter dropped 80 pairs.
- 3 epochs, 111 minutes on one T4.
- Dev chrF++ rose from 80.6 to 82.7, mostly flat after step 2,500. Best checkpoint: step 4,000.

**Domain test, scored against teacher drafts (UNVERIFIED).** This measures how close each system is to the teacher, not true quality. The teacher scores ~99.9 by construction.

| Language | Base chrF++ | LoRA chrF++ | Δ (95% CI), p | Term acc. base → LoRA |
|---|---|---|---|---|
| Hindi | 86.64 | 87.36 | +0.75 (−0.64, 2.24), p=0.15 | 95.0 → 95.0 |
| Konkani | 70.78 | 76.85 | +6.08 (4.38, 7.86), p<0.001 | 93.8 → 96.9 |
| Maithili | 74.06 | 77.19 | +3.08 (1.27, 5.00), p=0.001 | 98.3 → 96.7 |
| Dogri | 75.62 | 82.60 | +6.99 (5.39, 8.53), p<0.001 | 98.3 → 91.4 |

**IN22-Gen (human references; this result is valid for the paper)**
- Base model chrF++ across the 22 languages: 30.6 (Kashmiri) to 66.2 (Urdu); Hindi 55.8.
- No forgetting: LoRA vs base on the 4 domain languages is within ±0.5 chrF++.

**Terminology finding** (`analyze_terminology.py` → `results/teacher_term_consistency.csv`)
- The teacher uses the glossary form in only 84–87% of the drafts that contain the term.
- Systematic wrong-sense renderings:
  - "phase" → चरण ("stage") in about 95% of hi/mai/doi drafts
  - "earthing" → पृथ्वी ("planet Earth") in Maithili
  - "conduit" → नाली
- The student inherits these. That explains the Dogri and Maithili term-accuracy drops (for example, सर्किट ब्रेकर → परिपथ ब्रेकर).
- Some misses are glossary problems rather than teacher errors: Dogri spelling मुक्ख for "main", and the formal term रिसाव धारा for "leakage current". **The glossary needs expert validation.**

**Metric fixes**
- Term matching now normalises Devanagari spelling variants: anusvara vs half-nasal, chandrabindu, nukta, hyphens.
- Accepted spelling variants are listed in `TERM_VARIANTS`; only same-word variants go there, never wrong-sense ones.
- `run_domain_eval.py --from-predictions` re-scores saved predictions without a GPU. Once the post-edits are done, the paper numbers can be computed locally.

### Decision: formal terminology register (2026-10-15)
- **Decision:** target text uses **native/standard technical terms, not English loanwords**. Loanwords are kept only where no established native term exists (cable, fuse, megger, main switch, terminal block).
- **Glossary:** moved to `backend/data/glossary/electrician_glossary.csv` (32 terms × 4 languages), with both registers. `formal` is active; `LE_TERM_REGISTER=loanword` switches back.
  - Hindi: 11 terms `standard` (NCERT/CSTT usage), 16 `proposed`, 5 `loanword_kept`.
  - Konkani, Maithili, Dogri: all 27 non-loanword terms are `proposed` and need a native-speaker technical check.
- **New metric:** `term_compliance`, a reference-free measure of how often the output uses the glossary term. It's reported next to the reference-based term accuracy.
- **Finding:** the teacher uses the formal term in only **32–40%** of term-bearing drafts, vs 84–87% for the loanword glossary (`results/teacher_term_consistency*.csv`). Raw distillation therefore teaches mostly the loanword or literal style, so terminology correction of the drafts (experiment 2) is required for the formal register.
- **Post-editing guide** updated: formal register, glossary usage, and the common wrong-sense words to fix.

### Next
1. **Glossary validation:** native speakers / instructors review the `proposed` formal entries per language. Edit the CSV directly.
2. **Post-edit the 4 test sheets** using the validated glossary. Then: `run_domain_eval --from-predictions … --require-human-refs` (CPU).
3. **Experiment 2, terminology-aware distillation:** make the teacher drafts follow the formal glossary, retrain, and compare with run 4.
4. **Ablations:** Hindi-only vs joint training, LoRA rank.
