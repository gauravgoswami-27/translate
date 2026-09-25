#!/usr/bin/env python3
"""Phase 4: fine-tuning Indic/NLLB translation model on domain parallel corpus."""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from backend.localization_engine.languages import DEFAULT_MODEL_NAME


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare and run translation model fine-tuning.")
    parser.add_argument("--train-csv", default="data/corpus/electrician_en_hi_train.csv")
    parser.add_argument("--target-lang", default="hin_Deva")
    parser.add_argument("--base-model", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--output-dir", default="models/finetuned_hin_Deva")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--prepare-only", action="store_true", help="Only export text pairs and metadata.")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = read_rows(Path(args.train_csv))
    src_sentences = [row["english_sentence"].strip() for row in rows if row["english_sentence"].strip()]
    tgt_sentences = [
        (row.get("target_sentence") or row.get("hindi_sentence") or "").strip()
        for row in rows
        if (row.get("target_sentence") or row.get("hindi_sentence") or "").strip()
    ]
    min_len = min(len(src_sentences), len(tgt_sentences))
    src_sentences = src_sentences[:min_len]
    tgt_sentences = tgt_sentences[:min_len]

    source_file = output_dir / "train.eng_Latn"
    target_file = output_dir / f"train.{args.target_lang}"
    source_file.write_text("\n".join(src_sentences), encoding="utf-8")
    target_file.write_text("\n".join(tgt_sentences), encoding="utf-8")

    metadata = {
        "base_model": args.base_model,
        "target_lang": args.target_lang,
        "train_csv": args.train_csv,
        "num_rows": min_len,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "status": "prepared",
    }
    (output_dir / "training_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    if args.prepare_only:
        print(f"Prepared fine-tuning parallel files in {output_dir}")
        return

    try:
        import torch
        from peft import LoraConfig, TaskType, get_peft_model
        from torch.utils.data import DataLoader, TensorDataset
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except Exception as exc:
        print(f"Prepared files, but skipped training because dependencies are missing: {exc}")
        return

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Starting LoRA fine-tuning on {device.upper()} ({min_len} training pairs)...")
    start_time = time.time()

    print(f"Loading tokenizer & model '{args.base_model}'...")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.base_model, trust_remote_code=True)
    
    if hasattr(tokenizer, "src_lang"):
        tokenizer.src_lang = "eng_Latn"
    if hasattr(tokenizer, "tgt_lang"):
        tokenizer.tgt_lang = args.target_lang

    # Apply LoRA to drastically reduce GPU VRAM requirements
    peft_config = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM,
        r=8,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj"],
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    model.to(device)

    if hasattr(tokenizer, "lang_code_to_id") and tokenizer.lang_code_to_id:
        src_text = src_sentences
        tgt_text = tgt_sentences
    else:
        try:
            from IndicTransToolkit.processor import IndicProcessor
            processor = IndicProcessor(inference=False)
            src_text = processor.preprocess_batch(src_sentences, src_lang="eng_Latn", tgt_lang=args.target_lang)
            tgt_text = processor.preprocess_batch(tgt_sentences, src_lang=args.target_lang, tgt_lang=args.target_lang)
        except Exception:
            src_text = src_sentences
            tgt_text = tgt_sentences

    # Tokenize inputs and targets cleanly
    inputs = tokenizer(src_text, max_length=128, truncation=True, padding=True, return_tensors="pt")
    
    try:
        targets = tokenizer(text_target=tgt_text, max_length=128, truncation=True, padding=True, return_tensors="pt")
    except Exception:
        targets = tokenizer(tgt_text, max_length=128, truncation=True, padding=True, return_tensors="pt")

    labels = targets["input_ids"].clone()
    if tokenizer.pad_token_id is not None:
        labels[labels == tokenizer.pad_token_id] = -100

    dataset = TensorDataset(inputs["input_ids"], inputs["attention_mask"], labels)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

    model.train()
    loss_history = []
    for epoch in range(1, args.epochs + 1):
        epoch_loss = 0.0
        batch_count = 0
        for b_input_ids, b_attn_mask, b_labels in loader:
            b_input_ids = b_input_ids.to(device)
            b_attn_mask = b_attn_mask.to(device)
            b_labels = b_labels.to(device)

            optimizer.zero_grad()
            outputs = model(input_ids=b_input_ids, attention_mask=b_attn_mask, labels=b_labels)
            loss = outputs.loss

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            epoch_loss += loss.item()
            batch_count += 1

        avg_loss = epoch_loss / max(1, batch_count)
        loss_history.append(avg_loss)
        print(f"Epoch {epoch}/{args.epochs} - Loss: {avg_loss:.4f}")

    training_time = time.time() - start_time
    print(f"Training completed in {training_time:.2f}s. Merging LoRA weights and saving checkpoint to {output_dir}...")

    merged_model = model.merge_and_unload()
    merged_model.save_pretrained(output_dir)
    try:
        tokenizer.save_pretrained(output_dir)
    except Exception as e:
        print(f"Note: Tokenizer save_pretrained warning: {e}")

    metadata.update({
        "status": "completed",
        "device": device,
        "device_name": torch.cuda.get_device_name(0) if device == "cuda" else "CPU",
        "training_time_seconds": round(training_time, 2),
        "final_loss": round(loss_history[-1], 4) if loss_history else None,
        "loss_history": [round(l, 4) for l in loss_history],
        "peft_lora": True,
    })
    (output_dir / "training_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved fine-tuned checkpoint and metadata in {output_dir}")


if __name__ == "__main__":
    main()
