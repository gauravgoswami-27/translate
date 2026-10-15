#!/usr/bin/env bash
# Build the zip to upload as a PRIVATE Kaggle Dataset (code + corpus, no PDFs/venv/models).
set -euo pipefail
cd "$(dirname "$0")/.."
out=kaggle/dist/vocational-nmt-bundle.zip
mkdir -p kaggle/dist && rm -f "$out"
# Version stamp: the notebook only accepts code folders that carry one (never old run outputs).
date -u +%Y%m%dT%H%M%SZ > kaggle/BUNDLE_VERSION
zip -qr "$out" kaggle/BUNDLE_VERSION \
  backend/*.py backend/requirements.txt \
  backend/localization_engine/*.py backend/api/*.py \
  backend/data/corpus_v2 backend/data/glossary \
  kaggle/requirements-kaggle.txt \
  -x '*/__pycache__/*' '*.pyc'
echo "Wrote $out ($(du -h "$out" | cut -f1))"
unzip -l "$out" | tail -n +4 | head -n -2 | awk '{print "  " $4}'
