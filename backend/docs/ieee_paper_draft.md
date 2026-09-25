# Domain-Specific Fine-Tuning of Indic Neural Machine Translation for Vocational Content Localization

**Abstract** — Technical and vocational education materials in India are predominantly published in English, presenting significant learning barriers for trainees in non-urban regional areas. While open-source multilingual neural machine translation (NMT) models cover all 22 scheduled Indian languages, their performance on specialized vocational terminology (e.g., electrical engineering, trade practicals) is often compromised by out-of-vocabulary errors and generic phrase translations. In this paper, we present a vocational domain localization engine that fine-tunes open multilingual NMT architectures (`ai4bharat/indictrans2` / `facebook/nllb-200`) on an electrician parallel corpus constructed directly from official NCVET and Bharat Skills textbooks. Using Parameter-Efficient Fine-Tuning with Low-Rank Adaptation (LoRA), we achieve substantial quality improvements across primary (Hindi: +37.06 BLEU, +56.80 chrF) and low-resource stretch targets (Konkani: +66.33 BLEU; Maithili: +62.13 BLEU; Dogri: +64.96 BLEU). Furthermore, we present a RESTful FastAPI backend architecture designed for seamless integration with national skill development LMS platforms.

---

## I. Introduction

India's National Skill Development Corporation (NSDC) and Directorate General of Training (DGT) manage vocational education for millions of students through Craftsmen Training Schemes (CTS) and Craft Instructor Training Schemes (CITS). However, technical training resources—such as electrician trade practical manuals, safety specifications, and workshop calculation textbooks—are primarily distributed in English.

Although open-source Indic NMT models (such as AI4Bharat's IndicTrans2 and Meta's NLLB-200) support translation across Indian languages, general-purpose models struggle with domain-specific electrician vocabulary (e.g., *megger*, *insulation resistance*, *earth tester*, *circuit breaker*, *busbar*).

This paper demonstrates:
1. Extraction and construction of an official electrician domain parallel corpus from government NCVET and Bharat Skills textbooks.
2. Parameter-efficient GPU fine-tuning using LoRA to adapt multilingual Indic NMT backbones on local compute constraints (NVIDIA GeForce RTX 3050 GPU, 4GB VRAM).
3. Empirical quantitative evaluation demonstrating BLEU score improvements from 11.24 to 48.30 (Hindi) and up to 77.35 on low-resource stretch languages (Konkani, Maithili, Dogri).
4. A production-ready FastAPI REST backend with dynamic domain routing for LMS integration.

---

## II. Related Work

Multilingual Neural Machine Translation for Indian languages has advanced significantly with datasets such as BPCC (Bharat Parallel Corpus Collection) and models like IndicTrans2. However, domain adaptation for technical and vocational domains remains underexplored. Traditional fine-tuning of full 600M+ parameter models requires substantial compute and risks catastrophic forgetting. Parameter-Efficient Fine-Tuning (PEFT) methods, specifically Low-Rank Adaptation (LoRA), inject trainable rank decomposition matrices into Transformer attention layers, reducing trainable parameters by over 99.8% while preserving general language fluency.

---

## III. Methodology & Corpus Construction

### A. Parallel Corpus Acquisition
Source materials were scraped and parsed from official NCVET, Bharat Skills, and NIMI Learning Online portals:
- *Electrician (Trade Practical)*: 350 pages
- *Electrician (Trade Theory - Vol 1)*: 336 pages
- *Electrician Question Bank & Practical Guides*

Sentences containing technical electrician entities were isolated, normalized, and paired with target translations across Hindi (`hin_Deva`), Konkani (`gom_Deva`), Maithili (`mai_Deva`), and Dogri (`doi_Deva`), retaining source provenance metadata for citation traceability.

### B. Fine-Tuning Setup
- **Model Backbone**: `facebook/nllb-200-distilled-600M` / `IndicTrans2`
- **LoRA Configuration**: Rank \(r = 8\), \(\alpha = 32\), dropout = 0.05, target modules: `q_proj`, `v_proj`
- **Trainable Parameters**: 1,179,648 out of 616,253,440 (0.1914% of total model parameters)
- **Optimizer**: AdamW, learning rate \(2 \times 10^{-4}\), batch size 2, 5 training epochs
- **Hardware**: NVIDIA GeForce RTX 3050 Laptop GPU (4GB VRAM, CUDA 13.0)

---

## IV. Experimental Results & Analysis

### A. Baseline vs. Fine-Tuned Performance
Evaluation was conducted on independent 60-sentence test corpora per language using SacreBLEU and character n-gram F-score (chrF):

| Target Language | Code | Baseline BLEU | Fine-Tuned BLEU | BLEU Gain | Baseline chrF | Fine-Tuned chrF | chrF Gain |
|---|---|---|---|---|---|---|---|
| **Hindi** | `hin_Deva` | 11.24 | **48.30** | **+37.06** | 13.72 | **70.52** | **+56.80** |
| **Konkani** | `gom_Deva` | 11.02 | **77.35** | **+66.33** | 22.66 | **83.67** | **+61.01** |
| **Maithili** | `mai_Deva` | 11.88 | **74.01** | **+62.13** | 12.84 | **79.68** | **+66.84** |
| **Dogri** | `doi_Deva` | 11.25 | **76.21** | **+64.96** | 23.11 | **83.97** | **+60.86** |

### B. Baseline Performance Across All 22 Scheduled Indian Languages (Table 1)

| Language | Code | Baseline BLEU | Baseline chrF | Language | Code | Baseline BLEU | Baseline chrF |
|---|---|---|---|---|---|---|---|
| Assamese | `asm_Beng` | 0.00 | 0.00 | Manipuri | `mni_Mtei` | 2.56 | 11.23 |
| Bengali | `ben_Beng` | 0.00 | 0.00 | Marathi | `mar_Deva` | 1.43 | 0.41 |
| Bodo | `brx_Deva` | 2.56 | 11.23 | Nepali | `npi_Deva` | 0.00 | 0.00 |
| Dogri | `doi_Deva` | 11.25 | 23.11 | Odia | `ory_Orya` | 0.00 | 0.00 |
| Gujarati | `guj_Gujr` | 1.42 | 0.41 | Punjabi | `pan_Guru` | 1.31 | 0.33 |
| Hindi | `hin_Deva` | 11.24 | 13.72 | Sanskrit | `san_Deva` | 0.00 | 0.00 |
| Kannada | `kan_Knda` | 1.43 | 0.40 | Santali | `sat_Olck` | 2.56 | 11.23 |
| Kashmiri | `kas_Arab` | 0.00 | 0.00 | Sindhi | `snd_Arab` | 1.35 | 2.20 |
| Konkani | `gom_Deva` | 11.02 | 22.66 | Tamil | `tam_Taml` | 2.61 | 5.85 |
| Maithili | `mai_Deva` | 11.88 | 12.84 | Telugu | `tel_Telu` | 1.43 | 0.39 |
| Malayalam | `mal_Mlym` | 1.43 | 0.38 | Urdu | `urd_Arab` | 0.88 | 0.08 |

---

## V. System Architecture & API Integration

The engine is exposed via a RESTful FastAPI service (`/translate`):
- When `domain == "electrician"`, the request router dynamically loads local fine-tuned LoRA checkpoints (`models/finetuned_<target_lang>`).
- For general requests, the system seamlessly routes queries through the baseline multilingual model.
- Designed as an integration plugin for NCVET / MSDE / ITI Learning Management Systems.

---

## VI. Conclusion

This research demonstrates that lightweight LoRA fine-tuning of open multilingual NMT backbones on official vocational training text produces dramatic improvements in domain translation fidelity (+37.06 to +66.33 BLEU points) while maintaining minimal compute requirements. The resulting dataset, fine-tuned models, and API backend establish a scalable foundation for digital content localization across India's vocational education ecosystem.

