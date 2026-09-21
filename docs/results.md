# Results

## Baseline Scores

`results/baseline_scores.csv` contains one row per scheduled Indian-language
target. In the current local run, the file is a smoke-test scaffold generated
with the glossary fallback and bundled sample sentences.

Replace this with a real IN22 run before using the table in a paper:

```bash
python3 run_baseline_eval.py
```

## Domain Comparison

`results/comparison_scores.csv` compares the baseline translator with the
domain/fine-tuned route on `data/corpus/electrician_en_hi_test.csv`.

The current local values should be interpreted only as pipeline verification
because:

- the model backend was forced to fallback mode,
- the seed corpus is machine-generated,
- no human validation or actual model fine-tuning has been completed.

## Qualitative Examples

`results/qualitative_examples.csv` contains 10 example rows with:

- English input,
- reference target sentence,
- baseline prediction,
- fine-tuned/domain prediction,
- expected target technical term.

Use this file to select examples for the discussion section after real model
fine-tuning has been completed.
