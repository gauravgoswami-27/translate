# Backend: model pipeline and API

Everything runs from the **repository root** as modules (`python -m backend.<script>`). Paths come from `localization_engine/paths.py` and can be overridden with `LE_DATA_DIR`, `LE_CORPUS_DIR`, `LE_MODELS_DIR` and `LE_RESULTS_DIR`. On Kaggle they point to `/kaggle/working`.

## Environments

| Use | Environment | Requirements |
|---|---|---|
| API / CPU inference | Python 3.12, `backend/.venv-api` | `requirements-api.txt` (transformers 4.46.x, needed by IndicTrans2's model code) |
| Corpus building, analysis | any recent Python, `backend/.venv` | `requirements.txt` |
| GPU training / evaluation | Kaggle, 2 x T4 | `../kaggle/requirements-kaggle.txt` |

## Pipeline

| Step | Script | Output |
|---|---|---|
| 1. Download the NIMI electrician books | `fetch_real_materials.py` | `data/raw/*.pdf` |
| 2. Extract and filter sentences; page-block train/dev/test split | `build_corpus.py` | `data/corpus_v2/en_sentences.csv` |
| 3. Teacher translations (IndicTrans2-1B, beam 5) | `generate_drafts.py` | `data/corpus_v2/drafts_<lang>.csv` |
| 4. Terminology repair of train/dev drafts (placeholders, validation, case endings) | `repair_drafts.py` | `data/corpus_v2/drafts_<lang>_formal.csv` |
| 5. LoRA fine-tuning of the 200M student (joint, all languages) | `finetune.py` | `models/it2_lora_*` |
| 6. Domain evaluation (compliance, chrF++, BLEU, bootstrap) | `run_domain_eval.py` | `results/domain_*` |
| 7. General benchmark (IN22-Gen) | `run_baseline_eval.py` | `results/in22_gen_*` |
| Analysis | `analyze_terminology.py`, `analyze_term_breakdown.py`, `analyze_case_endings.py` | `results/*.csv` |
| Demo data | `export_frontend_results.py` | `../frontend/src/data/results.json` |

Steps 3–7 need a GPU and run on Kaggle (see `../kaggle/README.md`). Each script has `--help`.

Quick single-sentence check:

```bash
python -m backend.baseline_inference --model backend/models/it2_lora_joint_formal_v2 \
  --text "Test the insulation with a megger." --target-lang hin_Deva
```

## Package `localization_engine/`

- `translator.py`: IndicTrans2 loading (base + LoRA), batched beam search, placeholder injection/restoration, case-ending re-attachment
- `terminology.py`: hybrid mode (re-translate with placeholders only when a glossary term is missing)
- `glossary.py`: loads `data/glossary/electrician_glossary.csv` (formal and loanword registers)
- `metrics.py`: Indic spelling normalisation, term compliance, chrF++/BLEU, paired bootstrap
- `languages.py`, `data.py`, `paths.py`: language codes, CSV I/O, file locations

## Models in `models/`

| Folder | Run | Description |
|---|---|---|
| `it2_lora_joint_formal_v2` | 6 | **default**: terminology-aware, case-fixed formal drafts (hi, gom, mai, doi) |
| `it2_lora_joint_formal` | 5 | terminology-aware, before the case-ending fix |
| `it2_lora_joint` | 4 | distilled on raw teacher drafts (comparison) |

Each folder holds the LoRA adapter (r=16, ~25 MB) and `training_metadata.json` (hyperparameters, data sizes, dev curve). The base model `ai4bharat/indictrans2-en-indic-dist-200M` is downloaded from Hugging Face.

## Data

`data/glossary/electrician_glossary.csv` has 32 terms × 9 languages × 2 registers with a review status (`standard`, `proposed`, `loanword_kept`). The corpus, drafts and results are **not** in the repository, because the source books are marked "not to be republished". Steps 1–4 rebuild them.
