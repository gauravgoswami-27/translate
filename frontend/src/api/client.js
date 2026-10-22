// Client for the local FastAPI service (backend/api/main.py).
// No fake fallback: if the API is down, callers get an ApiError and show how to start it.

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
export const START_COMMAND = 'backend/.venv-api/bin/uvicorn backend.api.main:app --port 8000';

export class ApiError extends Error {
  constructor(message, { status = 0, offline = false } = {}) {
    super(message);
    this.status = status;
    this.offline = offline;
  }
}

async function request(path, { method = 'GET', body, signal } = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      signal,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    throw new ApiError(`Can't reach the translation API at ${API_BASE_URL}.`, { offline: true });
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const detail = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join('; ') : data.detail;
    throw new ApiError(detail || `The API returned an error (HTTP ${res.status}).`, { status: res.status });
  }
  return res.json();
}

export const api = {
  health: (signal) => request('/health', { signal }),
  translate: ({ text, targetLang, domain = 'electrician', model = 'auto', terminology = 'hybrid' }, signal) =>
    request('/translate', {
      method: 'POST',
      signal,
      body: { text, target_lang: targetLang, domain, model, terminology },
    }),
  translateBatch: ({ texts, targetLang, domain = 'electrician', model = 'auto', terminology = 'hybrid' }, signal) =>
    request('/translate/batch', {
      method: 'POST',
      signal,
      body: { texts, target_lang: targetLang, domain, model, terminology },
    }),
};
