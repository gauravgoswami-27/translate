#!/usr/bin/env python3
"""Step 3 (GPU): LoRA fine-tuning of IndicTrans2 (en-indic, dist-200M) on the electrician corpus.

Adapted from AI4Bharat's reference script (IndicTrans2/huggingface_interface/train_lora.py):
IndicProcessor preprocessing, a left-padding seq2seq collator, Seq2SeqTrainer with dev-set chrF++
model selection and early stopping. Only the LoRA adapter (a few MB) is saved.

Joint multilingual run (default, all four domain languages):
    python -m backend.finetune --run-name joint
Single-language run (ablation):
    python -m backend.finetune --langs hin_Deva --run-name hi_only
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import random
import time
from collections import Counter

from backend.localization_engine.data import load_pairs
from backend.localization_engine.languages import DEFAULT_MODEL_NAME, DOMAIN_LANGS, SOURCE_LANG
from backend.localization_engine.paths import CORPUS_DIR, MODELS_DIR
from backend.localization_engine.translator import load_indic_processor


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LoRA fine-tuning of IndicTrans2 on the domain corpus.")
    p.add_argument("--base-model", default=DEFAULT_MODEL_NAME)
    p.add_argument("--langs", default=",".join(DOMAIN_LANGS))
    p.add_argument("--run-name", default="joint")
    p.add_argument("--epochs", type=float, default=3)
    p.add_argument("--max-steps", type=int, default=-1, help="Overrides --epochs; use ~20 for a smoke test.")
    # Peak memory is dominated by the logits (batch x target length x ~122k vocab), so keep the
    # per-device batch small and reach an effective batch of 64 through accumulation.
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--grad-accum", type=int, default=4)
    p.add_argument("--eval-batch-size", type=int, default=16)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--warmup-steps", type=int, default=300)
    p.add_argument("--weight-decay", type=float, default=0.01)
    p.add_argument("--label-smoothing", type=float, default=0.1)
    p.add_argument("--lora-r", type=int, default=16)
    p.add_argument("--lora-alpha", type=int, default=32)
    p.add_argument("--lora-dropout", type=float, default=0.1)
    p.add_argument("--lora-targets", default="q_proj,k_proj,v_proj,out_proj,fc1,fc2")
    p.add_argument("--eval-steps", type=int, default=500)
    p.add_argument("--dev-per-lang", type=int, default=200, help="Dev sentences per language used for model selection.")
    p.add_argument("--patience", type=int, default=4)
    p.add_argument("--max-length", type=int, default=256, help="Source truncation length (tokens).")
    p.add_argument("--max-target-tokens", type=int, default=160, help="Drop pairs whose target is longer.")
    p.add_argument("--max-length-ratio", type=float, default=3.0,
                   help="Drop pairs whose target/source token ratio is larger (degenerate teacher drafts).")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


class IndicSeq2SeqCollator:
    """Same behaviour as IndicTransToolkit's IndicDataCollator (which is broken in 1.1.1:
    it imports `pad_without_fast_tokenizer_warning` inside the class body):
    sources are LEFT-padded (as in IndicTrans2 training), labels right-padded with -100."""

    def __init__(self, tokenizer, model=None, pad_to_multiple_of: int | None = 8, label_pad_token_id: int = -100):
        self.tokenizer = tokenizer
        self.model = model
        self.pad_to_multiple_of = pad_to_multiple_of
        self.label_pad_token_id = label_pad_token_id

    def __call__(self, features: list[dict]) -> dict:
        import numpy as np
        import torch

        labels = [list(f["labels"]) for f in features]
        inputs = [{k: v for k, v in f.items() if k != "labels"} for f in features]

        max_len = max(len(label) for label in labels)
        if self.pad_to_multiple_of:
            max_len = -(-max_len // self.pad_to_multiple_of) * self.pad_to_multiple_of
        padded = np.full((len(labels), max_len), self.label_pad_token_id, dtype=np.int64)
        for row, label in enumerate(labels):
            padded[row, : len(label)] = label

        original_side = self.tokenizer.padding_side
        self.tokenizer.padding_side = "left"
        try:
            batch = self.tokenizer.pad(
                inputs, padding="longest", pad_to_multiple_of=self.pad_to_multiple_of, return_tensors="pt"
            )
        finally:
            self.tokenizer.padding_side = original_side

        batch["labels"] = torch.from_numpy(padded)
        if self.model is not None and hasattr(self.model, "prepare_decoder_input_ids_from_labels"):
            batch["decoder_input_ids"] = self.model.prepare_decoder_input_ids_from_labels(labels=batch["labels"])
        return batch


def build_dataset(langs: list[str], split: str, processor, tokenizer, args, limit_per_lang: int | None) -> tuple:
    """Returns (tokenized dataset, filter statistics)."""
    from datasets import Dataset

    src_all, tgt_all, lang_all = [], [], []
    for lang in langs:
        sources, targets = load_pairs(lang, split, CORPUS_DIR)
        if limit_per_lang:
            paired = list(zip(sources, targets))
            random.Random(args.seed).shuffle(paired)
            sources, targets = (list(x) for x in zip(*paired[:limit_per_lang]))
        # Source gets the "eng_Latn <tgt_lang>" tags; targets are normalised only.
        src_all += processor.preprocess_batch(sources, src_lang=SOURCE_LANG, tgt_lang=lang, is_target=False)
        tgt_all += processor.preprocess_batch(targets, src_lang=lang, tgt_lang=SOURCE_LANG, is_target=True)
        lang_all += [lang] * len(sources)
        print(f"  {split:5s} {lang}: {len(sources)} pairs")

    def tokenize(batch):
        model_inputs = tokenizer(batch["src"], truncation=True, padding=False, max_length=args.max_length)
        with tokenizer.as_target_tokenizer():
            # No truncation here: over-long targets are dropped below rather than cut mid-sentence.
            labels = tokenizer(batch["tgt"], padding=False)
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    dataset = Dataset.from_dict({"src": src_all, "tgt": tgt_all, "lang": lang_all}).shuffle(seed=args.seed)
    dataset = dataset.map(tokenize, batched=True, remove_columns=["src", "tgt"])

    def keep(example) -> bool:
        n_tgt, n_src = len(example["labels"]), len(example["input_ids"])
        return n_tgt <= args.max_target_tokens and n_tgt <= args.max_length_ratio * n_src

    before = Counter(dataset["lang"])
    tgt_lengths = sorted(len(x) for x in dataset["labels"])
    dataset = dataset.filter(keep)
    after = Counter(dataset["lang"])
    stats = {
        "label_tokens_p50": tgt_lengths[len(tgt_lengths) // 2],
        "label_tokens_p99": tgt_lengths[int(0.99 * (len(tgt_lengths) - 1))],
        "label_tokens_max": tgt_lengths[-1],
        "dropped_per_lang": {lang: before[lang] - after[lang] for lang in before},
    }
    print(f"  {split}: label tokens p50={stats['label_tokens_p50']} p99={stats['label_tokens_p99']} "
          f"max={stats['label_tokens_max']}; dropped {stats['dropped_per_lang']}")
    return dataset.remove_columns(["lang"]), stats


def main() -> None:
    args = parse_args()
    langs = args.langs.split(",")
    output_dir = MODELS_DIR / f"it2_lora_{args.run_name}"
    output_dir.mkdir(parents=True, exist_ok=True)

    import numpy as np
    import torch
    import transformers
    import peft
    from peft import LoraConfig, get_peft_model
    from sacrebleu.metrics import BLEU, CHRF
    from transformers import (
        AutoModelForSeq2SeqLM,
        AutoTokenizer,
        EarlyStoppingCallback,
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
        set_seed,
    )

    set_seed(args.seed)
    token = os.getenv("HF_TOKEN")
    print(f"Loading {args.base_model} ...")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True, token=token)
    model = AutoModelForSeq2SeqLM.from_pretrained(
        args.base_model, trust_remote_code=True, attn_implementation="eager", token=token
    )
    model.set_label_smoothing(args.label_smoothing)
    processor = load_indic_processor(inference=False)

    print("Building datasets ...")
    train_ds, train_filter = build_dataset(langs, "train", processor, tokenizer, args, None)
    dev_ds, dev_filter = build_dataset(langs, "dev", processor, tokenizer, args, args.dev_per_lang)

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=args.lora_targets.split(","),
        bias="none",
        task_type="SEQ_2_SEQ_LM",
    )
    model = get_peft_model(model, lora_config)
    trainable, total = model.get_nb_trainable_parameters()
    print(f"Trainable params: {trainable:,} / {total:,} ({100 * trainable / total:.2f}%)")

    bleu, chrf_pp = BLEU(), CHRF(word_order=2)

    def compute_metrics(eval_preds):
        preds, labels = eval_preds
        preds = np.where(preds == -100, tokenizer.pad_token_id, preds)
        labels = np.where(labels == -100, tokenizer.pad_token_id, labels)
        with tokenizer.as_target_tokenizer():
            pred_text = [x.strip() for x in tokenizer.batch_decode(preds, skip_special_tokens=True)]
            ref_text = [x.strip() for x in tokenizer.batch_decode(labels, skip_special_tokens=True)]
        return {
            "chrF++": chrf_pp.corpus_score(pred_text, [ref_text]).score,
            "BLEU": bleu.corpus_score(pred_text, [ref_text]).score,
        }

    fp16 = torch.cuda.is_available()
    training_args = Seq2SeqTrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="inverse_sqrt",
        warmup_steps=args.warmup_steps,
        weight_decay=args.weight_decay,
        adam_beta2=0.98,
        max_grad_norm=1.0,
        fp16=fp16,
        eval_strategy="steps",
        save_strategy="steps",
        eval_steps=args.eval_steps,
        save_steps=args.eval_steps,
        logging_steps=50,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="chrF++",
        greater_is_better=True,
        predict_with_generate=True,
        generation_max_length=args.max_target_tokens + 32,
        generation_num_beams=4,
        group_by_length=True,
        dataloader_num_workers=2,
        report_to="none",
        seed=args.seed,
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=dev_ds,
        data_collator=IndicSeq2SeqCollator(tokenizer=tokenizer, model=model),
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=args.patience)],
    )

    start = time.time()
    trainer.train()
    train_minutes = (time.time() - start) / 60
    final_dev = trainer.evaluate()

    model.save_pretrained(output_dir)  # adapter only
    metadata = {
        "base_model": args.base_model,
        "langs": langs,
        "train_pairs": len(train_ds),
        "dev_pairs": len(dev_ds),
        "length_filter": {"train": train_filter, "dev": dev_filter},
        "hyperparameters": {k: v for k, v in vars(args).items()},
        "trainable_params": trainable,
        "total_params": total,
        "best_checkpoint": trainer.state.best_model_checkpoint,
        "best_dev_chrF++": trainer.state.best_metric,
        "final_dev_metrics": final_dev,
        "train_minutes": round(train_minutes, 1),
        "log_history": trainer.state.log_history,
        "environment": {
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
            "gpu_count": torch.cuda.device_count(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "peft": peft.__version__,
        },
    }
    (output_dir / "training_metadata.json").write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    print(f"Saved LoRA adapter + metadata to {output_dir} ({train_minutes:.1f} min).")


if __name__ == "__main__":
    main()
