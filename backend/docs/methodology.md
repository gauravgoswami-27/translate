# Methodology & Experimental Setup

## Model Architecture

The project fine-tunes neural machine translation models for English-to-Indic vocational domain translation.
- **Base Architecture**: Multi-lingual Seq2Seq translation backbone (`facebook/nllb-200-distilled-600M` / `IndicTrans2`).
- **Target Language**: Hindi (`hin_Deva`) primary, extensible to Konkani (`gom_Deva`), Maithili (`mai_Deva`), Dogri (`doi_Deva`).
- **Fine-Tuning Technique**: Parameter-Efficient Fine-Tuning using **LoRA (Low-Rank Adaptation)**:
  - Rank \(r = 8\), \(\alpha = 32\), dropout = 0.05
  - Target projection modules: `q_proj`, `v_proj`
  - Trainable parameters: 1,179,648 (0.19% of total parameters)
  - Optimizer: AdamW, learning rate \(2 \times 10^{-4}\)
  - Hardware: NVIDIA GeForce RTX 3050 Laptop GPU (4GB VRAM, CUDA 13.0)

## Real Domain Corpus Construction

Source materials were scraped and extracted directly from official NCVET / Bharat Skills / NIMI government vocational electrician textbooks & trade practical manuals:
1. `Electrician (Trade Practical).pdf` (350 pages, 456KB extracted text)
2. `Electrician (Trade Theory) - (Volume - 1).pdf` (336 pages, 603KB extracted text)
3. `Electrician Question Bank.pdf`

- **Extraction**: `extract_terms.py --from-raw` identified domain-specific technical terminology (`live wire`, `insulation resistance`, `megger`, `voltage stabilizer`, `ammeter`, `voltmeter`, `earth tester`, `circuit breaker`, `transformer`, `capacitor`).
- **Provenance**: Every extracted parallel text entry retains source file metadata (`source` field) for citation traceability.
- **Corpus Split**: 240 parallel training pairs (`electrician_en_hi_train.csv`) and 60 test pairs (`electrician_en_hi_test.csv`).

## Evaluation Protocol

Evaluation measures overall translation quality and domain-specific term fidelity using SacreBLEU:
1. **SacreBLEU**: Standard corpus-level BLEU score.
2. **chrF**: Character n-gram F-score.
3. **Domain Term Match Rate**: Ratio of translations preserving mandatory target technical terminology.
