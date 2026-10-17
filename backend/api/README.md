# Vocational Content Localization Engine: REST API (local)

FastAPI service for English → Indic translation of electrician training content. It's designed as an integration-ready endpoint for LMS platforms (NCVET / MSDE / ITI portals). This is an architecture demonstration, not a live integration.

## Models
| key | model | notes |
|---|---|---|
| `base` | IndicTrans2 en-indic dist-200M | all 22 languages |
| `raw` | base + LoRA from run 4 (`models/it2_lora_joint`) | distilled on raw teacher drafts |
| `formal` | base + LoRA from run 5 (`models/it2_lora_joint_formal`) | terminology-aware, formal register (default for electrician) |

With `model: "auto"`, `domain: "electrician"` routes Hindi, Konkani, Maithili and Dogri to `formal`; everything else goes to `base`.

## Setup (once)
```bash
# Python 3.12 environment (IndicTrans2's model code needs transformers 4.46.x)
uv venv -p 3.12 backend/.venv-api
VIRTUAL_ENV=backend/.venv-api uv pip install --index-strategy unsafe-best-match -r backend/requirements-api.txt
# access to the gated base model (accept its terms on huggingface.co first)
backend/.venv-api/bin/hf auth login
```
The models download on first use (~1.1 GB) and are cached in `~/.cache/huggingface`. Inference runs on CPU unless a CUDA build of PyTorch and a working NVIDIA driver are present.

## Run
From the repository root:
```bash
backend/.venv-api/bin/uvicorn backend.api.main:app --port 8000
# optional: LOCALIZATION_PRELOAD=formal,base loads the models at startup instead of on the first request
```
Interactive docs: http://localhost:8000/docs

## Endpoints
- `GET /health`: device, available and loaded models, domain model, terminology register
- `GET /languages`: the 22 supported languages and the 4 domain languages
- `GET /glossary/{target_lang}`: formal glossary (terms, variants, review status)
- `POST /translate`
  ```json
  {"text": "Check the three phase supply.", "target_lang": "hin_Deva",
   "domain": "electrician", "model": "auto", "terminology": "none"}
  ```
  Returns `translated_text`, the `model` used, `backend`, `latency_ms`, a `warning` if any, and `glossary_terms`: each glossary term found in the source, with its formal term and whether the output used it.
- `POST /translate/batch`: `{"texts": [...], ...}`, up to 64 sentences per request

`terminology` (electrician requests only): `"hybrid"` (default) translates normally and re-translates with entity placeholders only the sentences where a glossary term is missing (`placeholder_retry: true` in the response). `"placeholder"` always forces the terms; run 5 found this costs fluency (−4 to −6 chrF++). `"none"` returns the raw model output.

## Notes
- Requests to the same model are serialised, because IndicTrans2's pre/post-processor keeps per-batch state.
- `LOCALIZATION_FORCE_FALLBACK=1` runs a glossary-substitution stand-in (clearly labelled `fallback`) for frontend work without a model.
- CORS allows `http://localhost:5173` (the Vite dev server) by default; override with `CORS_ORIGINS`.
