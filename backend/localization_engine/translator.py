"""IndicTrans2 model loading and (batched) translation.

``model_name_or_path`` may be a Hugging Face model id, a local full checkpoint,
or a LoRA adapter folder produced by ``finetune.py`` (detected through its
``adapter_config.json``; the base model is loaded and the adapter merged in).
"""

from __future__ import annotations

import json
import os
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


def load_indic_processor(inference: bool = True):
    try:
        from IndicTransToolkit.processor import IndicProcessor
    except ImportError:  # older toolkit releases
        from IndicTransToolkit import IndicProcessor
    return IndicProcessor(inference=inference)


def resolve_adapter(path: str) -> tuple[str, Optional[str]]:
    """Return (base_model, adapter_dir_or_None) for a model path."""
    config_file = Path(path) / "adapter_config.json"
    if config_file.exists():
        base = json.loads(config_file.read_text())["base_model_name_or_path"]
        return base, str(path)
    return path, None


class Translator:
    """Translate English text with IndicTrans2.

    If the model stack is missing, falls back to a clearly-labelled glossary
    substitution (``backend == "fallback"``). Set ``allow_fallback=False`` to fail fast;
    all experiment scripts do this so results can never silently come from the fallback.
    """

    def __init__(
        self,
        model_name_or_path: str = DEFAULT_MODEL_NAME,
        device: Optional[str] = None,
        allow_fallback: bool = True,
        force_fallback: bool = False,
        fp16: bool = True,
    ) -> None:
        self.model_name_or_path = str(model_name_or_path)
        self.device_name = device
        self.allow_fallback = allow_fallback
        self.fp16 = fp16
        self.backend = "fallback"
        self.warning: Optional[str] = None
        self._torch = None
        self._tokenizer = None
        self._model = None
        self._processor = None

        if not force_fallback:
            self._load()

    # ------------------------------------------------------------------ loading

    def _load(self) -> None:
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except Exception as exc:  # pragma: no cover - depends on optional stack
            self._fallback_or_raise(f"Model dependencies are unavailable: {exc}")
            return

        try:  # pragma: no cover - needs model weights
            device = self.device_name or ("cuda" if torch.cuda.is_available() else "cpu")
            base_model, adapter = resolve_adapter(self.model_name_or_path)
            token = os.getenv("HF_TOKEN")

            tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True, token=token)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                base_model,
                trust_remote_code=True,
                attn_implementation="eager",
                low_cpu_mem_usage=True,
                token=token,
            )
            if adapter:
                from peft import PeftModel

                model = PeftModel.from_pretrained(model, adapter).merge_and_unload()

            model.to(device)
            if device.startswith("cuda") and self.fp16:
                model.half()
            model.eval()

            self._torch = torch
            self._tokenizer = tokenizer
            self._model = model
            self._processor = load_indic_processor(inference=True)
            self.device_name = device
            self.backend = "indictrans2_lora" if adapter else "indictrans2"
            self.warning = None
        except Exception as exc:
            self._fallback_or_raise(f"Could not load IndicTrans2 model '{self.model_name_or_path}': {exc}")

    def _fallback_or_raise(self, warning: str) -> None:
        if not self.allow_fallback:
            raise RuntimeError(warning)
        self.warning = warning
        self.backend = "fallback"

    def unload(self) -> None:
        """Release the model and clear the CUDA cache."""
        self._model = None
        self._tokenizer = None
        self._processor = None
        if self._torch is not None and self._torch.cuda.is_available():
            import gc

            gc.collect()
            self._torch.cuda.empty_cache()

    # -------------------------------------------------------------- translation

    def translate(self, text: str, target_lang: str, source_lang: str = SOURCE_LANG) -> TranslationResult:
        validate_target_lang(target_lang)
        if not text or not text.strip():
            raise ValueError("Input text must not be empty.")

        if self.backend == "fallback":
            translated = glossary_translate(text.strip(), target_lang)
        else:
            translated = self.translate_batch([text.strip()], target_lang, source_lang=source_lang)[0]

        return TranslationResult(
            translated_text=translated,
            backend=self.backend,
            model_name_or_path=self.model_name_or_path,
            warning=self.warning,
        )

    def translate_batch(
        self,
        texts: list[str],
        target_lang: str,
        source_lang: str = SOURCE_LANG,
        batch_size: int = 32,
        num_beams: int = 5,
        max_length: int = 256,
        max_tokens: int = 8000,
        show_progress: bool = False,
    ) -> list[str]:
        """Translate many sentences; output order matches input order.

        Batches are capped both by ``batch_size`` and by a token budget
        (sentences x padded source length x beams <= ``max_tokens``), so batches of
        long sentences shrink automatically. On CUDA OOM the budget is halved and
        the batch retried.
        """
        validate_target_lang(target_lang)
        if self.backend == "fallback":
            return [glossary_translate(t, target_lang) for t in texts]
        assert self._model is not None and self._tokenizer is not None and self._processor is not None

        # Length-sorted (longest first) batches waste little padding and hit any OOM early.
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]), reverse=True)
        outputs: list[str] = [""] * len(texts)
        progress = None
        if show_progress:
            try:
                from tqdm.auto import tqdm

                progress = tqdm(total=len(texts), desc=f"translate {target_lang}", unit="sent")
            except ImportError:
                pass

        start = 0
        while start < len(order):
            idx = order[start : start + batch_size]
            inputs = self._encode([texts[i] for i in idx], source_lang, target_lang)
            src_len = inputs["input_ids"].shape[1]
            allowed = max(1, max_tokens // (src_len * num_beams))
            if allowed < len(idx):
                idx = idx[:allowed]
                self._reset_processor(target_lang)
                inputs = self._encode([texts[i] for i in idx], source_lang, target_lang)

            try:
                with self._torch.inference_mode():
                    generated = self._model.generate(
                        **inputs,
                        use_cache=True,
                        min_length=0,
                        # Targets are rarely >2x the source length; stops runaway generations.
                        max_length=min(max_length, 2 * src_len + 16),
                        num_beams=num_beams,
                        num_return_sequences=1,
                    )
            except self._torch.cuda.OutOfMemoryError:
                if max_tokens <= 256:
                    raise
                max_tokens //= 2
                print(f"CUDA OOM; retrying with max_tokens={max_tokens}")
                del inputs
                self._reset_processor(target_lang)
                self._torch.cuda.empty_cache()
                continue

            decoded = self._tokenizer.batch_decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=True)
            for i, translation in zip(idx, self._processor.postprocess_batch(decoded, lang=target_lang)):
                outputs[i] = translation
            start += len(idx)
            if progress is not None:
                progress.update(len(idx))

        if progress is not None:
            progress.close()
        return outputs

    def _encode(self, sentences: list[str], source_lang: str, target_lang: str):
        # IndicProcessor queues one placeholder map per preprocessed sentence and
        # postprocess_batch consumes them, so every preprocess must be followed by
        # exactly one postprocess (or a _reset_processor call).
        batch = self._processor.preprocess_batch(sentences, src_lang=source_lang, tgt_lang=target_lang)
        return self._tokenizer(
            batch, truncation=True, padding="longest", return_tensors="pt", return_attention_mask=True
        ).to(self.device_name)

    def _reset_processor(self, target_lang: str) -> None:
        """Drop queued placeholder maps from a preprocessed batch that was not translated."""
        self._processor.postprocess_batch([], lang=target_lang)
