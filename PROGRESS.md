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

### Experiment 2 implemented: terminology-aware distillation (A) + constrained decoding (B)
- **Version kept:** git tag `v1-raw-distillation`, on branch `indictrans2-pipeline`.
  - The run-4 adapter stays in `models/it2_lora_joint`; the new one goes to `models/it2_lora_joint_formal`.
  - Raw drafts are unchanged; repaired drafts go to separate `drafts_*_formal.csv` files.
  - Run-4 results renamed to `*_run4.csv`; new results are tagged `run5`.
  - Notebook renamed to `kaggle/run4_raw_distillation.ipynb`.
- **(A) `repair_drafts.py`:**
  - The 1B teacher re-translates each train/dev draft that misses a glossary term (about 60% of term-bearing drafts), using lexically constrained beam search that forces the glossary term or a variant.
  - Outputs are validated: term present; term not tacked on after the final punctuation (a known failure mode of constrained search, seen in testing); length within 0.7–1.5× of the original.
  - Failures are excluded from training. Test drafts are left untouched so the human references aren't biased.
- **(B) Constrained decoding** in `Translator.translate_batch(constraints=…)`, used for any system with a `+cd` suffix in `run_domain_eval`:
  - Sentences are batched per constraint set.
  - Alternatives that are token-prefixes of each other are pruned (Hugging Face rejects them).
- **Evaluation:**
  - systems `base`, `lora`, `lora_formal` and `teacher`, each optionally with `+cd`
  - paired bootstrap of every system against base, vectorised (about 1 s instead of about 5 min)
  - `--from-predictions` merges several prediction files
- **Verified on Kaggle's exact library versions** (throwaway Python 3.12 environment with transformers 4.46.3 and sacrebleu 2.4.3, using a tiny public model): constrained decoding raises compliance from 0% to 98.6%; repair, validation, failed-row exclusion and evaluation all run end to end.
- **Not yet run:** anything with the real IndicTrans2 models (gated). The run-5 notebook's cell 4 smoke-tests a 20-sentence repair and prints examples.
- **Kaggle:** `kaggle/run5_terminology_aware.ipynb`. The bundle (33 MB) now includes the raw drafts and the run-4 adapter, so no other inputs are needed.

### Kaggle run 5 attempt 1: smoke test failed
- **Crash:** building the forced-term token ids. IndicTrans2's remote tokenizer switches itself back to source mode after each call, so a second call inside `as_target_tokenizer()` parsed Hindi as a tagged source sentence. Reproduced locally with a public copy of the same tokenizer code.
- **Fix:** one batched tokenizer call per context; verified with the real tokenizer.
- **Side observation from the same log:** base 200M renders "three phase supply and earthing" as तीन चरणों की आपूर्ति और मिट्टी ("three stages … and soil"). A clean example of the terminology problem for the paper.

### Kaggle run 5 attempt 2: constrained search unusable; switched to placeholder injection
- **Constrained beam search on the real 1B teacher** (20-sentence smoke test): only **5/20** repairs valid. In 15 cases the forced term was tacked on after the sentence, and it ran at ~1.5 s/sentence (more than 3 h per GPU for the full repair). It also crashed at the end on a missing output folder (fixed).
- **New default: placeholder injection.**
  - Each English glossary term in the source is replaced by an IndicTrans2 entity placeholder (`< IDn >`, numbered after the toolkit's own placeholders).
  - The model copies the placeholder into the right position, at normal decoding speed, and the glossary term is substituted back.
  - Restoration handles bracket variants, Devanagari spellings of "ID", and attached case endings (Maithili `<ID2>क` → `…क`).
  - Unit-tested locally, plus an end-to-end test on Kaggle's library versions.
- **Evaluation:** the systems now include `+ph` (placeholder injection) next to `+cd` (constrained decoding, kept as a weak baseline). Both are interesting for the paper: same goal, very different fluency.

### Kaggle run 5: terminology-aware distillation (2026-10-15/16)
**Draft repair (placeholder method)**
- 98.7% success in every language (hi 3494/3557, gom 3827/3869, mai 3431/3476, doi 3677/3725), ~7 minutes per language.
- Failures excluded from training (mostly the model dropping the placeholder).

**Training `joint_formal`**
- 96,074 pairs, 117 minutes. Dev chrF++ peaked at 82.14 (step 4,500; scored against the repaired drafts).

**Formal-glossary compliance, test set (reference-free; this is the main result)**

| | base | lora (run 4) | **lora_formal** | teacher |
|---|---|---|---|---|
| hi | 61.4 | 62.1 | **98.6** | 62.9 |
| gom | 39.3 | 20.7 | **95.7** | 25.0 |
| mai | 64.3 | 63.6 | **98.6** | 64.3 |
| doi | 55.7 | 59.3 | **98.6** | 55.7 |

**chrF++ against teacher drafts (UNVERIFIED and biased *against* formal outputs: the references use loanwords)**
- lora_formal is 2–3.5 points below lora. It is still significantly above base for gom (+2.1) and doi (+3.6); Hindi is −2.4.
- Expect this to change with formal post-edited references.

**Inference-time alternatives**
- `+ph` (placeholder): ≥97% compliance on any model, but −4 to −6 chrF++. The model loses context around the opaque placeholder.
- `+cd` (constrained decoding): 100% compliance but badly damaged output (Hindi base+cd BLEU 78→47). It inserts terms mid-word, e.g. द्विती **विभवांतर** टर्मिनलों.
- Exception: `lora_formal+cd` is close to `lora_formal`, because the model already produces the term, so the constraint rarely has to intervene.

**Forgetting (IN22-Gen chrF++, base → lora_formal)**
- hi 55.77→55.31, gom 43.71→43.51, mai 47.68→47.47, doi 54.02→54.15. Within ±0.5, so no forgetting.

**Takeaway for the paper:** terminology-aware distillation gives near-complete adherence to the chosen register *without* inference-time machinery or general-domain loss. The inference-time alternatives either hurt fluency (placeholders) or break it (constrained decoding).

### Next
2. **Glossary validation** of the `proposed` formal entries (native speakers / instructors). If entries change, re-run run 5.
   - Note for the paper: the placeholder method cannot inflect the inserted term. That's fine for Hindi (separate postpositions); worth checking in the Maithili outputs.
3. **Post-edit the 4 test sheets**, then rescore locally: `run_domain_eval --from-predictions …_run5.csv --require-human-refs`.
4. **Ablations:** Hindi-only vs joint training, LoRA rank.

### Local API (2026-10-17)
- **New environment** `backend/.venv-api` (Python 3.12, torch 2.5.1 CPU, transformers 4.46.3), pinned in `backend/requirements-api.txt`. The main venv's Python 3.14 / transformers 4.57 can't run IndicTrans2's model code.
- **GPU:** the NVIDIA driver isn't loaded on this machine (nouveau is active), so the API runs on CPU until the driver is repaired.
- **`backend/api/main.py` rewritten:**
  - models `base` / `raw` (run 4) / `formal` (run 5); auto-routing sends electrician requests in the 4 domain languages to `formal`
  - optional `terminology: placeholder` mode
  - per-response glossary report (term found, formal term used)
  - `/translate/batch`, `/languages`, `/glossary/{lang}`
  - per-model locks (IndicProcessor state isn't thread-safe)
  - all routes tested in fallback mode
- **Frontend:** the offline fallback no longer claims to be the fine-tuned model.
- **First real test passed** (Hugging Face login done): formal model, CPU, about 0.9 s per sentence; "three phase … earthing" → त्रिकला … भूसंपर्कन.
- **Found and fixed:**
  1. Rare glossary terms (live wire, neutral wire, …) aren't learned → new **hybrid** terminology mode (`localization_engine/terminology.py`; API default; `+hy` in evaluation): placeholder retry only where a term is missing. 100% compliance at −0.02 to −0.4 chrF++.
  2. Placeholder repair detached Maithili/Konkani case endings → `attach_case_suffixes`, applied in restoration and to the existing repaired drafts (1,050 mai + 427 gom). **Retraining (run 6) needed** to fix the model itself; hybrid mode re-attaches them until then.

### Run 6 prepared (2026-10-17)
- **Notebook:** `kaggle/run6_case_fixed.ipynb`, from the generator `kaggle/build_run6_notebook.py` (kept in the repo).
- **Bundle:** `20261017T103217Z` (42 MB), including the case-fixed formal drafts.
- **GPU 0:** `joint_formal_v2` → evaluation (plain + `+hy`) → IN22 forgetting check.
- **GPU 1:** `joint_formal_v2_s43` (seed variance) → `hi_formal_v2` (Hindi-only ablation) → their evaluations.
- **Evaluation:** any adapter can now be evaluated as `lora_<run>`.

## Paper material
Observations, methodology (replication guide) and references are kept in `paper/` (OBSERVATIONS.md, METHODOLOGY.md, references.bib), updated after each run.
