"""Model loading and translation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .glossary import glossary_translate
from .languages import DEFAULT_MODEL_NAME, SOURCE_LANG, validate_target_lang


@dataclass(frozen=True)
class TranslationResult:
    translated_text: str
    backend: str
    model_name_or_path: str
    warning: Optional[str] = None


class Translator:
    """Translate English text with IndicTrans2 when available.

    If model dependencies/checkpoints are missing, the class falls back to a
    transparent glossary backend. Set ``allow_fallback=False`` to fail fast.
    """

    def __init__(
        self,
        model_name_or_path: str = DEFAULT_MODEL_NAME,
        device: Optional[str] = None,
        allow_fallback: bool = True,
        force_fallback: bool = False,
    ) -> None:
        self.model_name_or_path = model_name_or_path
        self.device_name = device
        self.allow_fallback = allow_fallback
        self.force_fallback = force_fallback
        self.backend = "fallback"
        self.warning: Optional[str] = None
        self._torch = None
        self._tokenizer = None
        self._model = None
        self._processor = None

        if not force_fallback:
            self._load_indictrans2()

    def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: str = SOURCE_LANG,
        max_new_tokens: int = 256,
    ) -> TranslationResult:
        validate_target_lang(target_lang)
        if not text or not text.strip():
            raise ValueError("Input text must not be empty.")

        clean_text = text.strip()
        if self.backend == "indictrans2":
            translated = self._translate_with_indictrans2(
                clean_text,
                source_lang=source_lang,
                target_lang=target_lang,
                max_new_tokens=max_new_tokens,
            )
        else:
            translated = glossary_translate(clean_text, target_lang)

        return TranslationResult(
            translated_text=translated,
            backend=self.backend,
            model_name_or_path=self.model_name_or_path,
            warning=self.warning,
        )

    def _load_indictrans2(self) -> None:
        try:
            import torch
            from IndicTransToolkit.processor import IndicProcessor
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except Exception as exc:  # pragma: no cover - depends on optional stack
            self._fallback_or_raise(f"IndicTrans2 dependencies are unavailable: {exc}")
            return

        try:  # pragma: no cover - depends on optional model files
            device = self.device_name or ("cuda" if torch.cuda.is_available() else "cpu")
            model_path = str(Path(self.model_name_or_path)) if Path(self.model_name_or_path).exists() else self.model_name_or_path
            tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_path, trust_remote_code=True)
            model.to(device)
            model.eval()
            self._torch = torch
            self._tokenizer = tokenizer
            self._model = model
            self._processor = IndicProcessor(inference=True)
            self.device_name = device
            self.backend = "indictrans2"
            self.warning = None
        except Exception as exc:
            self._fallback_or_raise(f"Could not load IndicTrans2 model '{self.model_name_or_path}': {exc}")

    def _fallback_or_raise(self, warning: str) -> None:
        if not self.allow_fallback:
            raise RuntimeError(warning)
        self.warning = warning
        self.backend = "fallback"

    def _translate_with_indictrans2(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        max_new_tokens: int,
    ) -> str:
        assert self._torch is not None
        assert self._tokenizer is not None
        assert self._model is not None
        assert self._processor is not None

        batch = self._processor.preprocess_batch([text], src_lang=source_lang, tgt_lang=target_lang)
        inputs = self._tokenizer(
            batch,
            truncation=True,
            padding="longest",
            return_tensors="pt",
            return_attention_mask=True,
        ).to(self.device_name)
        with self._torch.inference_mode():
            generated_tokens = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                num_beams=5,
                num_return_sequences=1,
            )
        decoded = self._tokenizer.batch_decode(
            generated_tokens.detach().cpu().tolist(),
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        return self._processor.postprocess_batch(decoded, lang=target_lang)[0]
