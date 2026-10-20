# Data Sources and Resources Ledger

Every external resource the project uses, everything derived from it, and the compute spent. **Update this file whenever a resource is added, a dataset is regenerated, or a run is made.** Citation keys refer to `references.bib`.

---

## 1. Source texts (English)

Publisher: National Instructional Media Institute (NIMI), Chennai, for the Directorate General of Training (DGT), Ministry of Skill Development and Entrepreneurship, Government of India `[nimi_electrician]`. Downloaded 2026-09-21 (first 3) and 2026-10-15 (other 6) by `backend/fetch_real_materials.py`; stored in `backend/data/raw/` (git-ignored).

| File | Scheme | URL (bharatskills.gov.in) | Size | Pages | Sentences kept |
|---|---|---|---|---|---|
| Electrician (Trade Theory) – Volume 1 | CITS, NSQF 5 | `/pdf/E_Books/CITS/159/English/Electrician%20(Trade%20Theory)%20-%20(Volume%20-%201).pdf` | 14.1 MB | 336 | 3,074 |
| Electrician (Trade Practical) | CITS, NSQF 5 | `/pdf/E_Books/CITS/159/English/Electrician%20(Trade%20Practical).pdf` | 9.1 MB | 350 | 736 |
| Electrician (question paper) | CITS | `/pdf/QuestionBank/CITS/159/English/TP/Electrician.pdf` | 0.3 MB | 1 | 4 |
| Electrician SEM1 Trade Theory | CTS | `/pdf/E_Books/Electrician_SEM1_TT.pdf` | 48.9 MB | 290 | 4,351 |
| Electrician SEM2 Trade Theory | CTS | `/pdf/E_Books/Electrician_SEM2_TT.pdf` | 12.2 MB | 330 | 4,846 |
| Electrician SEM3 Trade Theory | CTS | `/pdf/E_Books/Electrician_SEM3_TT.pdf` | 9.9 MB | 250 | 4,353 |
| Electrician SEM4 Trade Theory | CTS | `/pdf/E_Books/Electrician_SEM4_TT.pdf` | 9.4 MB | 260 | 4,706 |
| Electrician SEM2 Trade Practical | CTS | `/pdf/E_Books/Electrician_SEM2_TP.pdf` | 6.2 MB | 172 | 1,377 |
| Electrician SEM4 Trade Practical | CTS | `/pdf/E_Books/Electrician_SEM4_TP.pdf` | 6.9 MB | 154 | 1,189 |
| **Total** | | | | **2,143** | **24,636** |

- "Sentences kept" counts sentences after filtering and global deduplication, so later documents lose sentences that duplicate earlier ones.
- **Licence:** the CITS books are marked **"© NIMI, NOT TO BE REPUBLISHED"**. Of the CTS books, the SEM1 file is marked CC BY; the others say not to republish. Check each file's notice before release.
- **Handling:** the extracted text and everything derived from it stays out of the public repository. It's kept locally and in a **private** Kaggle dataset.
- **No official Indian-language editions** of these books were found (search on 2026-10-15), so there's no human parallel data.

## 2. Pretrained models

| Model | Role | Hugging Face id | Revision seen on Kaggle | Licence | Access |
|---|---|---|---|---|---|
| IndicTrans2 en-indic 1B | teacher (drafts, repair) | `ai4bharat/indictrans2-en-indic-1B` | `89cd0007fd7b9e0693a2fd4404d187e07dac79fd` | MIT (verify on model card) | gated (auto-approved) |
| IndicTrans2 en-indic dist-200M | student / base | `ai4bharat/indictrans2-en-indic-dist-200M` | `2cfd0a20057756d756bf3e53528f492afc52f91a` | MIT (verify) | gated (auto-approved) |
| NLLB-200 distilled 600M | v1 pilot only (discarded) | `facebook/nllb-200-distilled-600M` | – | CC-BY-NC 4.0 | open |

Citation: `[gala2023indictrans2]`; NLLB `[nllb2022]`. The revisions come from the remote-code module paths in the run logs. Pin them (`revision=`) for exact replication.

## 3. Benchmarks

| Resource | Use | Source | Licence |
|---|---|---|---|
| IN22-Gen (1,024 sentences, 22 languages + English) | general-domain Table 1 and forgetting check | `ai4bharat/IN22-Gen`, test split (gated) | CC-BY-4.0 `[gala2023indictrans2]` |

## 4. Terminology resources (glossary)

File: `backend/data/glossary/electrician_glossary.csv`, with 32 English terms × 9 languages × 2 registers (formal, loanword).

| Resource | Used for | How |
|---|---|---|
| NCERT Science, Class X (Hindi medium) `[ncert_science10]` | Hindi `standard` entries (भूसंपर्कन, विद्युन्मय तार, उदासीन तार, संधारित्र, प्रतिरोध, …) | author's knowledge of the textbook terms; edition to cite |
| CSTT technical terminology `[cstt]` | Hindi formal coinages (कला = phase, परिपथ वियोजक, वोल्टता, …) | author's knowledge; marked `proposed` where uncertain |
| Wikipedia interlanguage titles | cross-check for the run-7 languages (e.g. Tamil முத்தறுவாய், மின்னழுத்தம்; Telugu విద్యుద్ఘాతము; Marathi विभवांतर) | `en.wikipedia.org` API `prop=langlinks`, retrieved 2026-10-20. **Partial:** the batch query was truncated by the API's link limit and a full re-query was cancelled. Saved as `backend/data/glossary/wikipedia_langlinks_partial.json`. Cite as "Wikipedia, accessed 2026-10-20" if used |
| Teacher output analysis | evidence of loanword / wrong-sense usage (चरण, पृथ्वी) | `backend/analyze_terminology.py` on the teacher drafts |

- **Review status:** not reviewed by native speakers (project decision, 2026-10-20). Hindi has 11 `standard` entries; every other non-loanword entry is `proposed`, i.e. author-curated.
- **Konkani, Maithili, Dogri:** Hindi register by analogy.
- **Run-7 languages:** the author's best formal terms, partly cross-checked with Wikipedia. Notable choices:
  - Tamil keeps native terms even for cable (மின்வடம்), fuse (உருகி) and terminal block (முனையத் தொகுதி).
  - Telugu and Kannada use the physics-textbook "phase" terms దశ / ಹಂತ.

## 5. Derived datasets (all in `backend/data/corpus_v2/`, git-ignored)

| File | Produced by | Run | Content |
|---|---|---|---|
| `en_sentences.csv` | `build_corpus.py` (seed 13) | local | 24,636 sentences: 24,082 train / 354 dev / 200 test |
| `drafts_{hi,gom,mai,doi}.csv` | `generate_drafts.py`, IndicTrans2-1B, beam 5 | Kaggle run 1 (2026-10-15) | raw teacher translations of all sentences |
| `drafts_{mr,gu,ta,te,kn}.csv` | same | run 7 | raw teacher translations (new languages) |
| `drafts_{lang}_formal.csv` | `repair_drafts.py` (placeholder method) | run 5 (4 languages), run 7 (5 languages) | terminology-repaired train/dev drafts; `term_repair` ∈ kept / repaired / failed |
| (same files, case fix) | `attach_case_suffixes`, post-hoc | 2026-10-17 | 1,050 Maithili + 427 Konkani repaired rows re-attached (`results/suffix_fix_stats.json`) |
| `postedit/test_{lang}.csv` | `generate_drafts.py` | runs 1 and 7 | 200 test sentences per language with teacher drafts, for post-editing (not done) |
| `frontend/src/data/results.json` | `export_frontend_results.py` | after each run | scores + glossary for the web demo (no book text) |

## 6. Software

PyMuPDF 1.28.2 `[pymupdf]`, IndicTransToolkit 1.1.1 `[indictranstoolkit]`, transformers 4.46.3 `[wolf2020transformers]`, PEFT 0.13.2 `[peft]`, accelerate 1.1.1, sacreBLEU 2.4.3 `[post2018call]`, PyTorch (2.11 on Kaggle, 2.5.1 CPU locally), FastAPI/uvicorn, React 19 / Vite / Tailwind 4 / Recharts (demo).

## 7. Compute ledger

Kaggle sessions on **2 × NVIDIA T4 (16 GB)**. Durations come from the session logs ("wall" = session length; GPU-hours ≈ 2 × wall when both GPUs were busy).

| Run | Date | Wall time | What used the GPUs | Notes |
|---|---|---|---|---|
| 1 | 2026-10-15 | ≈ 69 min | teacher drafts, 4 languages × 24,636 (2 GPUs, ~30 min/language) | training then failed (toolkit collator bug) |
| 2–3 | 2026-10-15 | ≈ 4 min each | smoke tests only | wrong bundle copy / OOM fix |
| 4 | 2026-10-15 | 139 min (8,317 s) | joint LoRA, 4 languages (111 min, 1 GPU) + evaluation + IN22-Gen 22 languages (GPU 1) | |
| 5 attempts | 2026-10-15 | ≈ 3 × 5 min | smoke tests (constrained decoding, placeholder) | |
| 5 | 2026-10-15/16 | 151 min (9,074 s) | repair 4 languages (~7 min each, 2 GPUs), LoRA 117 min, 10-system evaluation | |
| 6 | 2026-10-17 | 162 min (9,739 s) | 2 × joint LoRA (seeds 42/43, ~122 min each, parallel) + Hindi-only (25 min) + evaluation + IN22 | |
| 7 | planned | ≈ 6 h (estimate) | drafts + repair 5 languages, joint-9 + new-5 LoRA (2 epochs), evaluation, IN22 | |
| 8 | planned | ≈ 2.5 h (estimate) | seed 44 + Hindi-only rank sweep | |

**Local CPU** (Intel i7 laptop, 16 threads, no usable GPU): corpus build (<1 min), hybrid evaluation of the run-5 model (9 min), API inference (~0.9 s/sentence), all re-scoring and analysis scripts (seconds).

Kaggle's free quota is 30 GPU-hours per week; runs 1–6 used roughly 17 GPU-hours in total.
