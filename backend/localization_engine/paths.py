"""Filesystem locations, resolved relative to the backend/ folder.

Every path can be overridden with an environment variable so the same code
runs locally and on Kaggle (where inputs are read-only under /kaggle/input and
outputs must go to /kaggle/working).
"""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _dir(env_var: str, default: Path) -> Path:
    value = os.getenv(env_var)
    return Path(value) if value else default


DATA_DIR = _dir("LE_DATA_DIR", BACKEND_DIR / "data")
RAW_DIR = _dir("LE_RAW_DIR", DATA_DIR / "raw")
CORPUS_DIR = _dir("LE_CORPUS_DIR", DATA_DIR / "corpus_v2")
MODELS_DIR = _dir("LE_MODELS_DIR", BACKEND_DIR / "models")
RESULTS_DIR = _dir("LE_RESULTS_DIR", BACKEND_DIR / "results")
