# API

FastAPI integration endpoint for the vocational localization engine.

Run locally:

```bash
uvicorn api.main:app --reload
```

For a fast offline demo without loading IndicTrans2:

```bash
LOCALIZATION_FORCE_FALLBACK=1 python3 -m uvicorn api.main:app --reload
```

Translate:

```bash
curl -X POST http://127.0.0.1:8000/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"Check the circuit breaker rating.","target_lang":"hin_Deva","domain":"electrician"}'
```

Response:

```json
{
  "translated_text": "...",
  "target_lang": "hin_Deva",
  "backend": "indictrans2",
  "model_name_or_path": "ai4bharat/indictrans2-en-indic-dist-200M",
  "warning": null
}
```

If `domain` is `electrician` and `models/finetuned_<target_lang>/` exists, the
API attempts to use that checkpoint. Otherwise it falls back to the baseline
translator. This is an architecture demonstration suitable for NCVET, MSDE, ITI,
or LMS-style integration experiments, not a hosted production service.
