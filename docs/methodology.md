# Methodology

## Model

The project targets AI4Bharat IndicTrans2 for English-to-Indic translation. The
default checkpoint is the smaller En-Indic distilled model:
`ai4bharat/indictrans2-en-indic-dist-200M`.

The code supports all 22 scheduled Indian-language targets for baseline
evaluation. Domain adaptation is scoped to Hindi first, with Konkani, Maithili,
and Dogri as stretch targets.

## Corpus Construction

The intended publishable corpus should be built from official PMKVY, NCVET, ITI,
or comparable vocational electrician material. Each row preserves provenance in
the `source` field.

Current local seed rows are generated from a transparent electrician glossary and
sentence templates. They are useful for testing pipeline mechanics, but they are
not human-verified. Every such row has:

```text
needs_manual_review=True
source=machine_seed_glossary_for_method_development
```

Corpus schema:

```text
id, english_term, target_term, hindi_term, english_sentence,
target_sentence, hindi_sentence, target_lang, source, needs_manual_review
```

## Fine-Tuning

`finetune.py --prepare-only` exports parallel text files:

- `train.eng_Latn`
- `train.<target_lang>`
- `training_metadata.json`

For paper-grade training, run the official IndicTrans2/fairseq fine-tuning
workflow using these exported files. Record the checkpoint, hardware, batch size,
epochs, training time, and random seed in the paper's reproducibility section.

## Evaluation

Baseline evaluation uses IN22 when available under `data/in22/`. The bundled
fallback sentences are only smoke-test inputs.

Domain evaluation computes:

- BLEU,
- chrF,
- exact technical-term match rate,
- qualitative before/after examples.

`results/comparison_scores.csv` and `results/qualitative_examples.csv` map
directly to the results and discussion sections of the paper.
