# Vocational Content Localization Engine - REST API

This API provides integration-ready translation endpoints for LMS (Learning Management System) platforms such as MSDE (Ministry of Skill Development and Entrepreneurship), NCVET (National Council for Vocational Education and Training), PMKVY, and ITI portals.

---

## Features

- **RESTful Endpoints**: Standardized HTTP JSON request and response interface (`/translate`, `/health`).
- **Dynamic Domain Routing**: Automatically routes English-to-Indic translation requests to domain-adapted fine-tuned model checkpoints (`models/finetuned_<target_lang>`) when `domain="electrician"` is requested; otherwise falls back to the baseline multi-lingual NMT model.
- **Multi-Language Support**: Supports Hindi (`hin_Deva`), Konkani (`gom_Deva`), Maithili (`mai_Deva`), Dogri (`doi_Deva`), and all 22 scheduled Indian languages.

---

## Server Launch

Launch the API server locally using `uvicorn`:

```bash
PYTHONPATH=. python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive Swagger UI documentation is available at `http://127.0.0.1:8000/docs`.

---

## Endpoint Specifications

### 1. Health Check (`GET /health`)

```bash
curl -X GET http://127.0.0.1:8000/health
```

**Response**:
```json
{
  "status": "ok",
  "baseline_backend": "indictrans2"
}
```

---

### 2. Translate Text (`POST /translate`)

**Request Headers**: `Content-Type: application/json`

**Payload Schema**:
```json
{
  "text": "Check the insulation resistance with a megger.",
  "target_lang": "hin_Deva",
  "domain": "electrician"
}
```

**Example Request**:
```bash
curl -X POST http://127.0.0.1:8000/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Inspect the circuit breaker before opening the control panel.",
    "target_lang": "hin_Deva",
    "domain": "electrician"
  }'
```

**Example Response**:
```json
{
  "translated_text": "नियंत्रण पैनल खोलने से पहले सर्किट ब्रेकर का निरीक्षण करें।",
  "target_lang": "hin_Deva",
  "backend": "indictrans2",
  "model_name_or_path": "models/finetuned_hin_Deva",
  "warning": null
}
```

---

## Integration Architecture for NCVET / MSDE LMS

```
+--------------------------+       JSON Request       +------------------------------------+
|  NCVET / ITI LMS Server  | -----------------------> |  Vocational Localization Engine    |
| (Course Content Platform)| <----------------------- |          FastAPI Server            |
+--------------------------+       JSON Response      +------------------------------------+
                                                                    |
                                                  +-----------------+-----------------+
                                                  |                                   |
                                       domain == "electrician"               domain == "general"
                                                  |                                   |
                                                  v                                   v
                                       Fine-Tuned Domain Model              Baseline Indic NMT Model
                                     (models/finetuned_<lang>)             (facebook/nllb / IndicTrans2)
```
