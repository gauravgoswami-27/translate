# IEEE paper: terminology-aware distillation (run 6, four languages)

IEEE conference format (`IEEEtran`, two columns, US letter). It covers run 6 and Hindi, Konkani, Maithili and Dogri. Runs 7 and 8 are not part of this paper.

| File | Content |
|---|---|
| `main.tex` | paper source |
| `references.bib` | bibliography for this paper (43 entries) |
| `make_figures.py` | builds `figures/*.pdf` (and `.png` previews) from `backend/results/` |
| `figures/` | Figs. 2–6 (Fig. 1, the pipeline, is TikZ inside `main.tex`) |
| `fonts/` | Noto Sans Devanagari UI, Regular and Bold (SIL Open Font License 1.1, see `fonts/OFL.txt`) |
| `main.pdf` | compiled paper |

## Build

The paper needs XeLaTeX because it sets Devanagari with `fontspec`.

```bash
cd paper/ieee
tectonic -X compile main.tex        # Tectonic 0.15; downloads its TeX bundle on first run
```

With TeX Live instead: `xelatex main && bibtex main && xelatex main && xelatex main`. TeX Gyre Termes is the Times-like body font, loaded by file name (`texgyretermes-*.otf`, in TeX Live's `tex-gyre` package). Devanagari is loaded from `fonts/`.

Rebuild the figures after any change to the result files:

```bash
backend/.venv/bin/python paper/ieee/make_figures.py
```

## Where the numbers come from

| Paper element | Source in `backend/results/` |
|---|---|
| Table I, corpus | `backend/data/corpus_v2/en_sentences.csv` (split counts), test-set term counts from `term_breakdown.csv` |
| Table III, repair | `term_repair_stats_hi_mai.json`, `term_repair_stats_gom_doi.json` |
| Table IV, settings | `backend/models/*/training_metadata.json` |
| Fig. 2, teacher consistency | `teacher_term_consistency.csv` (loanword totals: `teacher_term_consistency_loanword.csv`) |
| Table V, wrong-sense | `wrong_sense.csv` (rows `teacher_drafts_train_dev`) |
| Table VI, Fig. 3, Fig. 4, Table VIII | `term_compliance_macro.csv` (pooled / macro), `domain_scores_UNVERIFIED_run6_all.csv` (chrF++, BLEU, bootstrap) |
| Table VII, examples | `domain_predictions_UNVERIFIED_run6_all.csv` (ids `elec_18810`, `elec_18813`, `elec_00149`) |
| Det. column (Table VIII), Table X | `case_endings.csv` |
| Fig. 5, Table IX | `in22_gen_scores.csv`, `in22_gen_lora*.csv` |
| Fig. 6 | `log_history` in `backend/models/*/training_metadata.json` |
| Hindi-only ablation | `domain_scores_UNVERIFIED_run6_hi.csv` |

Means in the text and Table VIII are averages of the four per-language scores. Where a value fell on a rounding boundary at two decimals, chrF++/BLEU were recomputed from the predictions with sacreBLEU.

## Before submission

- [x] Author block: Gaurav, Aastha Shukla, Anubhav Sharma (AIT-CSE, Chandigarh University). If the venue is double-blind, anonymise it for the review copy.
- [ ] Check the venue's page limit. The paper is 8 pages including references.
- [ ] If the test sets get post-edited: re-score (CPU), then update Tables VI and VIII, Fig. 4, and the "What the References Measure" subsection. The current text treats chrF++/BLEU as agreement with the teacher.
- [ ] Check every `references.bib` entry against the publisher's page. The NCERT and CSTT entries need an edition or year.
- [ ] Run IEEE PDF eXpress on `main.pdf`. All fonts are embedded; `pdffonts main.pdf` lists them.
- [ ] The glossary was not reviewed by native speakers (decision of 2026-10-20). The paper states this in Limitations. If a review happens, recompute compliance with the revised glossary.
