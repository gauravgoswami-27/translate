# Experimental Results & Quantitative Findings

## Comparative Performance (Baseline vs Fine-Tuned Model)

Experimental evaluation conducted on the official 60-sentence `electrician_en_hi_test.csv` parallel dataset:

| Model Variant | BLEU Score | chrF Score | Term Match Rate | Translation Engine |
|---|---|---|---|---|
| **Baseline (NLLB-200 600M)** | **11.24** | **13.72** | **75.0%** | PyTorch GPU (CUDA) |
| **Fine-Tuned Domain Model (LoRA)** | **48.30** | **70.52** | **68.3%** | PyTorch GPU (CUDA) |
| **Gain / Improvement** | **+37.06** | **+56.80** | — | — |

> [!NOTE]
> Fine-tuning with LoRA on the electrician domain corpus yielded a **+37.06 BLEU score improvement** and **+56.80 chrF score improvement** over the baseline translation model.

## Training Loss Progression

- **Epoch 1**: Loss = 1.2402
- **Epoch 2**: Loss = 0.2930
- **Epoch 3**: Loss = 0.1722
- **Epoch 4**: Loss = 0.1222
- **Epoch 5**: Loss = 0.0924
- **Total Training Time**: 60.84 seconds on NVIDIA GeForce RTX 3050 Laptop GPU.

## Qualitative Examples

| ID | English Source Sentence | Baseline Translation | Fine-Tuned Model Output | Target Term |
|---|---|---|---|---|
| `hi_raw_0146` | Resistance of heating coil | प्रतिरोध of heating coil | हीटिंग कॉइल का प्रतिरोध | प्रतिरोध |
| `hi_raw_0167` | Internal resistance | Internal प्रतिरोध | आंतरिक प्रतिरोध | प्रतिरोध |
| `hi_raw_0018` | Test and verify the voltage of 1 Ph & 3 ph | 1 Ph & 3 ph के वोल्टेज का परीक्षण और सत्यापन | 1 Ph & 3 ph वोल्टेज का परीक्षण और सत्यापन | वोल्टेज |
| `hi_raw_0061` | Note down voltmeter & Ammeter readings | वोल्टमीटर और एम्पमीटर रीडिंग को नोट करें | वोल्टमीटर और अमीटर रीडिंग नोट करें | अमीटर |
