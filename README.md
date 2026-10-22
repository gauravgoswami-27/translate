# Vocational Content Localization Engine

English → Indian-language translation of electrician (ITI / NIMI) training material, with consistent **formal technical terminology**.

The model is the 200M-parameter [IndicTrans2](https://github.com/AI4Bharat/IndicTrans2) student with a LoRA adapter. It was distilled from IndicTrans2-1B on 24,636 sentences from nine official electrician trade books. Before training, the teacher's translations are **repaired** with a glossary: each technical term is passed through as a placeholder, the formal term is inserted, and detached case endings are re-attached. The result is a model that uses the formal glossary term on its own, with no special decoding.

| Languages | Hindi, Konkani, Maithili, Dogri (domain model); all 22 scheduled languages through the base model |
|---|---|
| Formal-term use, average over term types | 90–99.6% (base model: 28–51%); 100% with the hybrid fallback |
| General-domain quality (IN22-Gen) | unchanged: within 0.41 chrF++ of the base model |

The frontend in this repository is a **demonstration** of the model. It is not a production application.

## Repository layout

```text
backend/
  localization_engine/   translator (placeholders, case endings, hybrid fallback), glossary, metrics, paths
  api/                   FastAPI service (REST endpoints used by the demo)
  models/                LoRA adapters: it2_lora_joint_formal_v2 (run 6, default),
                         it2_lora_joint (run 4, raw distillation), it2_lora_joint_formal (run 5)
  data/glossary/         32-term electrician glossary, 9 languages x 2 registers (formal, loanword)
  *.py                   pipeline: corpus → teacher drafts → repair → fine-tuning → evaluation
kaggle/                  notebooks and bundle script for GPU training on Kaggle (2 x T4)
frontend/                demonstration web app (React + Vite)
```

## Quick start (API + demo)

Requirements: Python 3.12, Node 20+, a Hugging Face account that has accepted the terms of
[`ai4bharat/indictrans2-en-indic-dist-200M`](https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M).

```bash
# 1. API (from the repository root)
uv venv -p 3.12 backend/.venv-api
VIRTUAL_ENV=backend/.venv-api uv pip install --index-strategy unsafe-best-match -r backend/requirements-api.txt
backend/.venv-api/bin/hf auth login
backend/.venv-api/bin/uvicorn backend.api.main:app --port 8000      # docs: http://localhost:8000/docs

# 2. Demo frontend
cd frontend && npm install && npm run dev                            # http://localhost:5173
```

On first use the base model (~1.1 GB) is downloaded from Hugging Face. The adapters are already in `backend/models/`. On a laptop CPU a sentence takes about 0.9 s.

```bash
curl -s localhost:8000/translate -H 'content-type: application/json' \
  -d '{"text": "Check the three phase supply and the earthing.", "target_lang": "hin_Deva", "domain": "electrician"}'
```

More detail: [`backend/README.md`](backend/README.md) (pipeline), [`backend/api/README.md`](backend/api/README.md) (endpoints), [`kaggle/README.md`](kaggle/README.md) (training), [`frontend/README.md`](frontend/README.md) (demo).

## What is not in this repository

- **Training text.** The source books are marked "not to be republished", so the extracted sentences, teacher translations and model predictions stay local and in a private Kaggle dataset. Rebuild them with the pipeline in `backend/` from the publicly downloadable PDFs.
- **Experiment outputs** (`backend/results/`), the research paper, and project notes are kept locally.
- **Extra adapters** (second seed, Hindi-only ablation) are not pushed.

## Limitations

- The domain test references are unedited teacher translations, so domain chrF++/BLEU measure agreement with the teacher, not human-judged quality.
- The glossary was curated by the authors (NCERT / CSTT usage for Hindi, analogous forms for the other languages) and has not been reviewed by native-speaker instructors.

## Authors

Gaurav, Aastha Shukla, Anubhav Sharma: AIT-CSE, Chandigarh University, Mohali, Punjab, India.
