# Research Observations (for the paper)

A living record of findings, numbers and their sources, kept separate from the engineering log (`PROGRESS.md`).
- **Status markers:** **[final]** means the number can go in the paper as is. **[provisional]** means it depends on references that aren't human-verified yet, or on a glossary still under review.
- **Citations:** keys like `[gala2023indictrans2]` refer to `paper/references.bib`.

---

## 1. Problem and setting
- **Problem:** vocational (ITI electrician) training material is published in English. Trainees need it in Indian languages, with **consistent, correct technical terminology**.
- **Languages:** Hindi (primary); Konkani, Maithili, Dogri (low-resource).
- **Terminology register (design decision, 2026-10-15):** formal/native technical terms (NCERT/CSTT style), not English loanwords. Loanwords are kept only where no established native term exists (cable, fuse, megger, main switch, terminal block).
  - *Paper note:* state this as a design choice with its trade-off. Formal terms may be less familiar to trainees than loanwords; a user study would be future work.

## 2. Earlier pilot (v1) and why it was discarded
- **Setup:** NLLB-200-distilled-600M `[nllb2022]` with LoRA `[hu2022lora]` on a 300-row corpus.
- **The corpus wasn't parallel:** targets were English sentences with only the term swapped (98% contained English words).
- **Two of the four languages were unsupported:** NLLB has no Konkani or Dogri. The model produced Portuguese/French for Konkani, and the reported "+66 BLEU" was an artefact.
- *Paper use:* one sentence in related work or methodology to motivate the IndicTrans2 choice. Report no v1 numbers.

## 3. Data
- **Source:** 9 official NIMI / DGT Electrician books (CITS and CTS Trade Theory, Trade Practical, question bank) `[nimi_electrician]`.
- **Extraction:** PyMuPDF `[pymupdf]`. pypdf split words across lines and was rejected.
- **Corpus:** **24,636 unique English sentences** after filtering (5–45 words, letter ratio, terminal punctuation, deduplication). **[final]**
- **Split:** by blocks of 10 consecutive pages: **24,082 train / 354 dev / 200 test**. Train sentences that near-duplicate test sentences (4-gram Jaccard ≥ 0.7) were removed (3 sentences). 150 of the 200 test sentences contain domain terms. **[final]**
- **No official Hindi edition** of the books was found, so there was no genuine parallel data. Training targets come from **forward translation by a teacher model** (sequence-level knowledge distillation) `[kim2016sequence]` `[zhang2016exploiting]`.
- **Teacher:** IndicTrans2-1B en-indic `[gala2023indictrans2]`. **Student:** IndicTrans2-dist-200M.
- **Teacher draft quality:**
  - no empty outputs
  - about 1.5% contain an English word
  - 18–30 repetitive drafts per 24.6k
  - length ratio (target/source words), median 0.82–1.13 by language **[final]**
- **Length filter at training time:** pairs dropped if the target exceeds 160 tokens or 3× the source; 15–31 per language. Label tokens: p50 = 25, p99 = 70, max = 228. **[final]**
- **Licensing:** CITS books are marked "NOT TO BE REPUBLISHED". The corpus text is kept out of the public repository. *Paper note:* say the corpus is available on request / for research, or release only IDs and scripts. Decide before submission.

## 4. Teacher terminology analysis (key finding #1)
Source: `backend/analyze_terminology.py` → `results/teacher_term_consistency*.csv`.
- **Loanword glossary (v1):** the teacher uses the glossary form in 84–87% of term-bearing drafts after spelling normalisation (75–84% before). **[final]**
- **Formal glossary:** the teacher uses the formal term in only **32–40%** of term-bearing drafts. **[provisional: glossary under review]**
- **Systematic wrong-sense renderings (qualitative, robust):**
  - *phase* → चरण ("stage/step"): about 95% of Hindi/Maithili/Dogri drafts containing "three phase" / "single phase". The CSTT term is कला.
  - *earthing* → पृथ्वी ("planet Earth") or मिट्टी ("soil"): about 40% of Maithili drafts; मिट्टी/धरती in Dogri. The NCERT term is भूसंपर्कन.
  - *live wire* → जीवित तार ("living wire"). The NCERT term is विद्युन्मय तार.
- **Same error in the base student:** "Check the three phase supply and the earthing" → तीन **चरणों** की आपूर्ति और **मिट्टी** की जाँच करें (IndicTrans2-200M). A good illustrative example for the introduction.
- **Measurement note:** orthographic variants (इन्सुलेशन / इंसुलेशन, anusvara vs half-nasal) made naïve string matching undercount term use by up to 8 points (Dogri). Normalisation is required. Describe it in the evaluation section.

## 5. Run 4: distillation on raw teacher drafts
Joint multilingual LoRA, r=16 on q/k/v/out/fc1/fc2: 6.5M trainable of 218M parameters (2.97%), 3 epochs, 111 min on a T4.
- **Domain chrF++ against teacher drafts** **[provisional, UNVERIFIED references]**:

  | Language | Base | LoRA | Δ (95% CI) |
  |---|---|---|---|
  | Hindi | 86.64 | 87.36 | +0.7 (n.s.) |
  | Konkani | 70.78 | 76.85 | +6.1 |
  | Maithili | 74.06 | 77.19 | +3.1 |
  | Dogri | 75.62 | 82.60 | +7.0 |

  - Gains concentrate in the low-resource languages; Hindi is already close to the teacher.
- **Distillation inherits the teacher's terminology.** Formal compliance doesn't improve (Hindi 61→62%), and for **Konkani it halves (39→21%)**: the student adopts the teacher's loanword habits. **[provisional: glossary]**
- **No catastrophic forgetting** `[thompson2019overcoming]`: on IN22-Gen, LoRA is within ±0.5 chrF++ of base. **[final]**

## 6. Run 5: terminology-aware distillation (key finding #2)
**Method:** repair the teacher's train/dev drafts so they follow the glossary, then distil.
- **First attempt, lexically constrained beam search** `[hokamp2017lexically]` `[post2018fast]` (Hugging Face `force_words_ids`) on the 1B teacher:
  - only **5/20** usable; in 15 cases the forced term was tacked on after the sentence
  - ~1.5 s per sentence
  - **Negative result worth reporting.**
- **Adopted method, placeholder injection:** the English glossary term is replaced by an IndicTrans2 entity placeholder (`<IDn>`). The model copies it to the grammatically right position, and the formal term is substituted back (in the spirit of `[luong2015addressing]` `[crego2016systran]`).
  - **Repair success: 98.7%** in every language (hi 3494/3557, gom 3827/3869, mai 3431/3476, doi 3677/3725), ~7 min per language on a T4. **[final for this glossary version]**
  - Failures (model dropped the placeholder, length, term outside the sentence) are excluded from training.
  - Test drafts were not repaired, so the post-editing seeds aren't biased toward the method.
- **Training (`joint_formal`):** 96,074 pairs, 117 min, best dev chrF++ 82.14.
- **Formal-term compliance on the test set** (reference-free) **[provisional: glossary]**:

  | | Base | LoRA (raw) | **LoRA (term-aware)** | Teacher |
  |---|---|---|---|---|
  | hi | 61.4 | 62.1 | **98.6** | 62.9 |
  | gom | 39.3 | 20.7 | **95.7** | 25.0 |
  | mai | 64.3 | 63.6 | **98.6** | 64.3 |
  | doi | 55.7 | 59.3 | **98.6** | 55.7 |

- **chrF++ against teacher drafts:** term-aware is 2–3.5 points below raw LoRA, but still significantly above base for gom (+2.1, p=0.02) and doi (+3.6, p=0.002). **Biased against formal output**, because the references use loanwords. Must be re-measured on post-edited formal references. **[provisional]**
- **No forgetting:** IN22-Gen chrF++ base → term-aware: hi 55.77→55.31, gom 43.71→43.51, mai 47.68→47.47, doi 54.02→54.15. **[final]**

## 7. Inference-time alternatives (key finding #3)
Same test set; compliance (%) / chrF++ against teacher drafts **[provisional]**.
- **Placeholder injection at inference (`+ph`):** ≥97% compliance on any model, but −4 to −6 chrF++ against the same model without it. Loss of context around the opaque placeholder.
- **Constrained decoding (`+cd`):** 100% compliance but severe damage, e.g. Hindi base BLEU 77.97 → 46.65. It inserts terms mid-word (द्विती **विभवांतर** टर्मिनलों) or tacks them on at the end.
- **Interaction:** `lora_formal+cd` ≈ `lora_formal` (Hindi chrF++ 83.50 vs 84.23), because the term-aware model already produces the term and the constraint rarely intervenes.
- **Message:** putting terminology into the training data beats enforcing it at decoding time. It reaches the same compliance without the fluency cost.

## 7b. Hybrid enforcement and two findings from local API testing (2026-10-17)
- **Rare terms aren't learned by distillation.** The formal model kept लाइव तार for "live wire" in every language. Training frequency (Hindi train sentences): live wire ~16, neutral wire 10, junction box 8, terminal block 6, safety shoes 2, phase tester 0, against hundreds to thousands for voltage, resistance and insulation. The 98–99% test compliance is dominated by frequent terms. **[final, qualitative + counts]**
- **Placeholder repair breaks attached case endings** (a limitation of the method). With `<IDn>` the teacher writes the ending as a separate word.
  - Maithili repaired drafts: 1,211 detached vs 100 attached, against 17 vs 1,269 in unrepaired drafts.
  - Konkani shows the same with च्या/ची/चेर.
  - The run-5 model learned it (विद्युतरोधन क परीक्षण).
  - Fix: language-specific re-attachment after restoration. Applied to 1,050 Maithili and 427 Konkani repaired drafts (`results/suffix_fix_stats.json`). Run 6 retrains on the fixed data.
  - Hindi and Dogri are unaffected (postpositions are separate words).
  - Caveat: for Konkani, joining doesn't add the oblique stem vowel (…नाच्या), so it's partially correct. Post-editors will see it.
- **Hybrid enforcement (`+hy`, also the API default):** translate normally; re-translate with placeholders only the sentences whose output misses a glossary term. On the test set (run-5 formal model, CPU), retries were needed for only 2, 6, 2 and 2 of 200 sentences (hi, gom, mai, doi). **[provisional: UNVERIFIED references, glossary]**

  | | lora_formal | +ph (always) | **+hy (hybrid)** |
  |---|---|---|---|
  | hi compliance / chrF++ | 98.6 / 84.23 | 98.6 / 82.29 | **100 / 84.21** |
  | gom | 95.7 / 72.84 | 100 / 71.48 | **100 / 72.44** |
  | mai | 98.6 / 75.16 | 100 / 73.41 | **100 / 74.82** |
  | doi | 98.6 / 79.17 | 99.3 / 77.61 | **100 / 78.89** |

  - Message: a terminology-aware model plus a targeted fallback gets full compliance at near-zero fluency cost. Always-placeholder costs 1.5–2 chrF++; constrained decoding is worse still.
- **Local inference speed (CPU, Intel i7 laptop, 200M + merged LoRA):** about 0.9 s per single sentence, 0.33 s per sentence in batches of 4. First load (download + merge) took about 6 minutes; later loads take about 6 seconds.

## 8. General benchmark: IN22-Gen [final]
IndicTrans2-dist-200M, English → 22 scheduled languages, 1,024 sentences each, chrF++ / BLEU (sacreBLEU `[post2018call]`, chrF++ `[popovic2017chrf]`):

| | | | | |
|---|---|---|---|---|
| asm 44.90/17.45 | ben 47.48/16.56 | brx 46.14/15.64 | doi 54.02/28.44 | guj 52.58/25.21 |
| hin 55.77/32.69 | kan 48.54/15.32 | kas 30.62/6.37 | gom 43.71/18.35 | mai 47.68/18.08 |
| mal 46.26/12.83 | mni 40.84/9.41 | mar 50.00/20.97 | npi 48.09/15.09 | ory 41.30/11.79 |
| pan 47.06/21.58 | san 35.22/8.63 | sat 33.67/5.60 | snd 35.15/14.09 | tam 48.91/13.95 |
| tel 51.52/18.23 | urd 66.23/45.15 | | | |

- **TODO before citing:** compare against the published IndicTrans2 numbers `[gala2023indictrans2]`. Our setup is 200M, beam 5, sacreBLEU default tokenisation, whereas AI4Bharat reports with IndicNLP tokenisation, so the BLEU values aren't directly comparable. Prefer chrF++.

## 9. Evaluation protocol (for the methods section)
- **Metrics:**
  - BLEU `[papineni2002bleu]` and chrF++ `[popovic2017chrf]` via sacreBLEU `[post2018call]`
  - **term accuracy:** counted only where the reference uses an accepted glossary form
  - **term compliance:** reference-free, share of source glossary terms rendered with an accepted form
- **Spelling normalisation for term matching only:** anusvara/half-nasal, chandrabindu, nukta, hyphens.
- **Significance:** paired bootstrap resampling, 1,000 samples, on chrF++, every system against base `[koehn2004statistical]`.
- **References:** 200 sentences per language, teacher drafts post-edited by fluent speakers using the formal glossary (pending).
  - Known risk: post-editing bias toward the draft system `[toral2019post]`. Mitigation: editors are told to rewrite freely, and test drafts are never terminology-repaired.

## 10. Limitations to state
- Training targets are machine-generated (distillation), not human translations.
- The glossary is hand-curated: Hindi has 11 `standard` entries; the rest are `proposed` pending expert review. Konkani, Maithili and Dogri entries are least certain.
- Placeholder insertion can't inflect the inserted term. That's fine for Hindi (separate postpositions); in Maithili the case endings attach after the placeholder.
- Single domain (electrician); a single seed so far.
- The domain test set is small (200 sentences per language).
- Formal terms may be less familiar to trainees (register trade-off).

## 11. Open items that affect the paper
- [ ] Glossary review → possibly re-run run 5 (~3 h on Kaggle).
- [ ] Post-edited test sets → final domain BLEU/chrF++/term accuracy (CPU rescoring).
- [ ] Optional ablations: Hindi-only vs joint training, LoRA rank, 3 seeds.
- [ ] Optional COMET `[rei2020comet]`. Check coverage for Konkani, Maithili and Dogri first.
