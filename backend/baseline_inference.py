#!/usr/bin/env python3
"""Quick English-to-Indic inference check (base model, or a LoRA adapter folder via --model)."""

from __future__ import annotations

import argparse
import json

from backend.localization_engine import Translator
from backend.localization_engine.languages import DEFAULT_MODEL_NAME


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Translate English text with IndicTrans2.")
    parser.add_argument("--text", required=True, help="English text to translate.")
    parser.add_argument("--target-lang", default="hin_Deva", help="IndicTrans2 target code, e.g. hin_Deva.")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="HF model id, local checkpoint, or LoRA adapter folder.")
    parser.add_argument("--device", default=None, help="Optional torch device, e.g. cpu or cuda.")
    parser.add_argument("--allow-fallback", action="store_true", help="Use the glossary backend if the model cannot load.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    translator = Translator(
        model_name_or_path=args.model,
        device=args.device,
        allow_fallback=args.allow_fallback,
    )
    result = translator.translate(args.text, target_lang=args.target_lang)
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
