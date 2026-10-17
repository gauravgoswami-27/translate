# Frontend

React 19 + Vite + Tailwind v4 + Recharts. Five pages: Translate, Compare, Results, Glossary, Course reader.
Light, dark and system themes (toggle in the header; `?theme=dark|light|system` in the URL also works).

## Run
```bash
# 1. API (repository root): see backend/api/README.md
backend/.venv-api/bin/uvicorn backend.api.main:app --port 8000
# 2. Frontend
cd frontend && npm install && npm run dev      # http://localhost:5173
```
The API address can be changed with `VITE_API_URL`.

## Data
The Results and Glossary pages read `src/data/results.json`, which is generated from the experiment outputs.
They work without the API. After each run, regenerate it:
```bash
python -m backend.export_frontend_results
```
Translate, Compare and Course reader call the API live. If it isn't running, they show how to start it (no fake fallback).

## Design notes
- Semantic colour tokens (`bg-surface`, `text-ink-2`, `border-line`, …) in `src/index.css`, with separately chosen light and dark values.
- Chart series use a validated colour-blind-safe palette with a fixed slot per system: base = blue, raw = orange, terminology-aware = aqua, teacher = yellow. Every chart has a table view.
- `?static` in the URL disables chart animation (used for headless screenshots).
