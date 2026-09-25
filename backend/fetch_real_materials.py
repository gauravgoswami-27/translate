#!/usr/bin/env python3
"""Download official Electrician vocational training PDF materials from Bharat Skills & NIMI."""

from __future__ import annotations

import os
import urllib.parse
import urllib.request
from pathlib import Path
from pypdf import PdfReader


URLS = [
    "https://bharatskills.gov.in/pdf/E_Books/CITS/159/English/Electrician%20(Trade%20Practical).pdf",
    "https://bharatskills.gov.in/pdf/E_Books/CITS/159/English/Electrician%20(Trade%20Theory)%20-%20(Volume%20-%201).pdf",
    "https://bharatskills.gov.in/pdf/QuestionBank/CITS/159/English/TP/Electrician.pdf",
]


def download_file(url: str, output_path: Path) -> bool:
    print(f"Downloading {url}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response, open(output_path, "wb") as out:
            out.write(response.read())
        print(f"Saved to {output_path} ({output_path.stat().st_size} bytes)")
        return True
    except Exception as exc:
        print(f"Could not download {url}: {exc}")
        return False


def extract_pdf_to_text(pdf_path: Path, txt_path: Path) -> None:
    print(f"Extracting text from {pdf_path.name}...")
    try:
        reader = PdfReader(str(pdf_path))
        text_pages = []
        for index, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                text_pages.append(f"--- Page {index+1} ---\n" + text.strip())
        full_text = "\n\n".join(text_pages)
        txt_path.write_text(full_text, encoding="utf-8")
        print(f"Extracted {len(reader.pages)} pages to {txt_path} ({len(full_text)} characters)")
    except Exception as exc:
        print(f"Error reading PDF {pdf_path}: {exc}")


def main() -> None:
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)

    for url in URLS:
        filename = os.path.basename(urllib.parse.unquote(url))
        pdf_path = raw_dir / filename
        txt_path = raw_dir / (pdf_path.stem + ".txt")

        if not pdf_path.exists():
            download_file(url, pdf_path)
        
        if pdf_path.exists() and not txt_path.exists():
            extract_pdf_to_text(pdf_path, txt_path)

    txt_files = list(raw_dir.glob("*.txt"))
    print(f"\nProcessing complete. Found {len(txt_files)} extracted text files in {raw_dir}:")
    for f in txt_files:
        print(f" - {f.name} ({f.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

