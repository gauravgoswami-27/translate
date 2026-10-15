#!/usr/bin/env python3
"""Download official Electrician training books (NIMI / Bharat Skills) into data/raw.

Licensing: the CITS books are marked "NOT TO BE REPUBLISHED"; some CTS semester
books are CC BY. Use the text for research, but keep any uploaded dataset private
(e.g. a private Kaggle Dataset) and cite the sources in the paper.

    python -m backend.fetch_real_materials
"""

from __future__ import annotations

import os
import urllib.parse
import urllib.request
from pathlib import Path

from backend.localization_engine.paths import RAW_DIR

URLS = [
    # Craft Instructor Training Scheme (CITS), NSQF level 5
    "https://bharatskills.gov.in/pdf/E_Books/CITS/159/English/Electrician%20(Trade%20Practical).pdf",
    "https://bharatskills.gov.in/pdf/E_Books/CITS/159/English/Electrician%20(Trade%20Theory)%20-%20(Volume%20-%201).pdf",
    "https://bharatskills.gov.in/pdf/QuestionBank/CITS/159/English/TP/Electrician.pdf",
    # Craftsmen Training Scheme (CTS), semester books
    "https://bharatskills.gov.in/pdf/E_Books/Electrician_SEM1_TT.pdf",
    "https://bharatskills.gov.in/pdf/E_Books/Electrician_SEM2_TT.pdf",
    "https://bharatskills.gov.in/pdf/E_Books/Electrician_SEM3_TT.pdf",
    "https://bharatskills.gov.in/pdf/E_Books/Electrician_SEM4_TT.pdf",
    "https://bharatskills.gov.in/pdf/E_Books/Electrician_SEM2_TP.pdf",
    "https://bharatskills.gov.in/pdf/E_Books/Electrician_SEM4_TP.pdf",
]


def download_file(url: str, output_path: Path) -> bool:
    print(f"Downloading {url} ...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
    except Exception as exc:
        print(f"  could not download: {exc}")
        return False
    if not payload.startswith(b"%PDF"):
        print("  server did not return a PDF; skipped")
        return False
    output_path.write_bytes(payload)
    print(f"  saved {output_path.name} ({len(payload) / 1e6:.1f} MB)")
    return True


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for url in URLS:
        pdf_path = RAW_DIR / os.path.basename(urllib.parse.unquote(url))
        if pdf_path.exists():
            print(f"Already present: {pdf_path.name}")
            continue
        download_file(url, pdf_path)
    print(f"\n{len(list(RAW_DIR.glob('*.pdf')))} PDFs in {RAW_DIR}")


if __name__ == "__main__":
    main()
