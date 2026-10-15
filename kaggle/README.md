# Training on Kaggle

## One-time setup
1. **Hugging Face:** log in and accept the terms (access is approved automatically) on:
   - https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M
   - https://huggingface.co/ai4bharat/indictrans2-en-indic-1B
   - https://huggingface.co/datasets/ai4bharat/IN22-Gen

   Then create a **read** token under Settings → Access Tokens.
2. **Build the bundle** locally, from the repo root:
   ```bash
   bash kaggle/make_bundle.sh      # -> kaggle/dist/vocational-nmt-bundle.zip (~1 MB)
   ```
3. **Kaggle → Datasets → New Dataset:** upload `vocational-nmt-bundle.zip`. Keep it **Private**, because the NIMI CITS books are marked "not to be republished".

## Each run
1. Kaggle → New Notebook → File → Import Notebook → `kaggle/indictrans2_pipeline.ipynb`.
2. In the right panel:
   - **Add Input:** your bundle dataset.
   - **Accelerator:** GPU T4 x2.
   - **Internet:** On.
   - **Add-ons → Secrets:** `HF_TOKEN` = your token, with notebook access enabled.
3. Run cells 1-4 interactively (setup and smoke test, about 5 minutes). If they pass, use **Save Version → Save & Run All**.
4. When it finishes, download `outputs.zip` from the version's Output tab and unzip it locally:
   - `corpus_v2/` → `backend/data/corpus_v2/` (drafts and post-editing sheets)
   - `it2_lora_joint/` → `backend/models/it2_lora_joint/`
   - `results/` → `backend/results/`

Expected time is about 3-4 hours in total, within Kaggle's 12-hour session limit and the 30 GPU-hours weekly quota. Drafts are written per language and skipped on re-run, so a crashed session can resume.

## After post-editing
Put the filled sheets in `backend/data/corpus_v2/postedit/`, rebuild the bundle, upload it as a new dataset version, and run only the setup cells plus:
```bash
python -m backend.run_domain_eval --adapter <path to it2_lora_joint> --require-human-refs
```
