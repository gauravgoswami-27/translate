#!/usr/bin/env python3
"""Generate kaggle/run7_new_languages.ipynb (reuses the setup cells of the run-5 notebook).

Run 7 = five more languages: Marathi, Gujarati, Tamil, Telugu, Kannada.
  1. teacher drafts + placeholder terminology repair for the 5 new languages (both GPUs)
  2. GPU 0: joint 9-language model (original 4 + new 5)     -> does adding languages hurt the original 4?
     GPU 1: 5-language model (new languages only)            -> joint-5 vs joint-9 for the new languages
  3. evaluation: base / teacher / both new models (+hybrid) on the new languages; joint-9 on all nine;
     IN22-Gen forgetting check for joint-9 on all nine.
The original four languages are not re-translated: their drafts ship in the bundle.

    python3 kaggle/build_run7_notebook.py
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
run5 = json.loads((HERE / "run5_terminology_aware.ipynb").read_text())
setup_cells = run5["cells"][1:4]  # copy stamped bundle, pinned install, HF token + access check

NEW = ["mar_Deva", "guj_Gujr", "tam_Taml", "tel_Telu", "kan_Knda"]
OLD = ["hin_Deva", "gom_Deva", "mai_Deva", "doi_Deva"]
GPU0_LANGS, GPU1_LANGS = ["mar_Deva", "tam_Taml", "guj_Gujr"], ["tel_Telu", "kan_Knda"]
ALL9 = ",".join(OLD + NEW)
NEW5 = ",".join(NEW)
# 9 languages x 24k pairs: 2 epochs (~6.8k steps) keep the session within ~6 h; dev curves of
# runs 4-6 were flat after ~2.5k steps. Smaller dev set per language keeps evaluation cheap.
TRAIN_FLAGS = "--drafts-variant formal --epochs 2 --eval-steps 1000 --dev-per-lang 100"

cells = []


def md(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": text.strip("\n")})


def code(text):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text.strip("\n")})


md(f"""
# Vocational NMT: run 7, five more languages (Marathi, Gujarati, Tamil, Telugu, Kannada)

1. **Teacher drafts + terminology repair** for the 5 new languages. GPU 0: {", ".join(GPU0_LANGS)}; GPU 1: {", ".join(GPU1_LANGS)}. The original 4 languages' drafts ship in the bundle and aren't re-translated.
2. **Training:** GPU 0 trains `joint9_formal` (all 9 languages); GPU 1 trains `new5_formal` (the 5 new languages only). Both run 2 epochs.
3. **Evaluation:**
   - base, teacher and both new models (plain and hybrid) on the new languages
   - `joint9_formal` on all nine
   - IN22-Gen forgetting check for `joint9_formal`

**Input:** only the latest bundle dataset. Use GPU T4 x2, Internet on, and the `HF_TOKEN` secret. Then **Save & Run All** (about 6 hours); the outputs end up in `/kaggle/working/outputs.zip`.
""")
cells.extend(setup_cells)
code("""
# 4. Smoke test (~6 min): Tamil + Marathi drafts and placeholder repair on 40 sentences, in a scratch corpus
def check(step):
    assert _exit_code == 0, f"{step} failed - see the output above"

import pandas as pd
SMOKE = Path("/kaggle/working/smoke_corpus")
SMOKE.mkdir(parents=True, exist_ok=True)
shutil.copy(CORPUS / "en_sentences.csv", SMOKE / "en_sentences.csv")
!LE_CORPUS_DIR=/kaggle/working/smoke_corpus CUDA_VISIBLE_DEVICES=0 python -m backend.generate_drafts --langs tam_Taml,mar_Deva --limit 120 --overwrite
check("draft smoke test")
!LE_CORPUS_DIR=/kaggle/working/smoke_corpus LE_RESULTS_DIR=/kaggle/working/smoke_results CUDA_VISIBLE_DEVICES=0 python -m backend.repair_drafts --langs tam_Taml,mar_Deva --limit 40 --overwrite
check("repair smoke test")
for s in ["ta", "mr"]:
    d = pd.read_csv(SMOKE / f"drafts_{s}_formal.csv", keep_default_na=False)
    d = d[d.term_repair != "kept"]
    print(s, d.term_repair.value_counts().to_dict())
    for _, r in d.head(4).iterrows():
        print(f"  [{r.term_repair}] {r.english_sentence[:80]}\\n     {r.target_sentence[:110]}")
""")
md("## Step 1: teacher drafts + terminology repair for the new languages (both GPUs)")
code(f"""
import torch
n_gpu = torch.cuda.device_count()
groups = {[GPU0_LANGS, GPU1_LANGS]!r} if n_gpu >= 2 else [{NEW!r}]
procs = []
for gpu, langs in enumerate(groups):
    l = ",".join(langs)
    chain = f"python -m backend.generate_drafts --langs {{l}} && python -m backend.repair_drafts --langs {{l}}"
    procs.append(subprocess.Popen(["bash", "-c", chain], env=dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu)),
                                  stdout=open(f"/kaggle/working/drafts_repair_gpu{{gpu}}.log", "w"), stderr=subprocess.STDOUT))
codes = [p.wait() for p in procs]
for gpu in range(len(groups)):
    print(open(f"/kaggle/working/drafts_repair_gpu{{gpu}}.log").read()[-1500:])
assert all(c == 0 for c in codes), codes
!cat backend/results/term_repair_stats_*.json
!python -m backend.analyze_terminology
""")
code(f"""
# Training smoke test (~3 min): 10 steps on all nine languages, then load the adapter
!CUDA_VISIBLE_DEVICES=0 python -m backend.finetune --drafts-variant formal --langs {ALL9} --run-name smoke --max-steps 10 --eval-steps 5 --dev-per-lang 4
check("training smoke test")
!python -m backend.baseline_inference --model backend/models/it2_lora_smoke --text "Check the voltage with a voltmeter." --target-lang tam_Taml
check("adapter loading")
shutil.rmtree("backend/models/it2_lora_smoke", ignore_errors=True)
""")
md("## Step 2: GPU 0 trains the 9-language model; GPU 1 trains the 5-language model, then evaluates the new languages")
gpu1_chain = (
    f"python -m backend.finetune {TRAIN_FLAGS} --langs {NEW5} --run-name new5_formal && "
    f"python -m backend.run_domain_eval --langs {NEW5} --systems base,teacher,lora_new5_formal,lora_new5_formal+hy --tag run7a"
)
code(f"""
gpu1 = None
if n_gpu >= 2:
    gpu1 = subprocess.Popen(["bash", "-c", {gpu1_chain!r}], env=dict(os.environ, CUDA_VISIBLE_DEVICES="1"),
                            stdout=open("/kaggle/working/new5_gpu1.log", "w"), stderr=subprocess.STDOUT)

!CUDA_VISIBLE_DEVICES=0 python -m backend.finetune {TRAIN_FLAGS} --langs {ALL9} --run-name joint9_formal
check("9-language fine-tuning")
""")
md("## Step 3: evaluation")
code(f"""
!CUDA_VISIBLE_DEVICES=0 python -m backend.run_domain_eval --langs {ALL9} --systems lora_joint9_formal,lora_joint9_formal+hy --tag run7b
check("9-language evaluation")
if IN22_OK:
    !CUDA_VISIBLE_DEVICES=0 python -m backend.run_baseline_eval --skip-base --adapter backend/models/it2_lora_joint9_formal --output backend/results/in22_gen_lora_joint9.csv
if gpu1 is not None:
    print("GPU 1 exit code:", gpu1.wait())
    print(open("/kaggle/working/new5_gpu1.log").read()[-3000:])
else:
    !CUDA_VISIBLE_DEVICES=0 bash -c {gpu1_chain!r}
!python -m backend.analyze_case_endings backend/results/domain_predictions_UNVERIFIED_run7b.csv
""")
code(f"""
# Package everything that must come back to your machine
out = Path("/kaggle/working/outputs")
shutil.rmtree(out, ignore_errors=True)
(out / "corpus_v2" / "postedit").mkdir(parents=True)
for s in ["mr", "gu", "ta", "te", "kn"]:
    for name in [f"drafts_{{s}}.csv", f"drafts_{{s}}_formal.csv"]:
        if (CORPUS / name).exists():
            shutil.copy(CORPUS / name, out / "corpus_v2")
    if (CORPUS / "postedit" / f"test_{{s}}.csv").exists():
        shutil.copy(CORPUS / "postedit" / f"test_{{s}}.csv", out / "corpus_v2" / "postedit")
for run in ["joint9_formal", "new5_formal"]:
    src = Path(f"backend/models/it2_lora_{{run}}")
    if src.exists():
        shutil.copytree(src, out / src.name, ignore=shutil.ignore_patterns("checkpoints"))
    else:
        print("missing:", src)
shutil.copytree("backend/results", out / "results")
for log in glob.glob("/kaggle/working/*.log"):
    shutil.copy(log, out)
shutil.make_archive("/kaggle/working/outputs", "zip", out)
!du -sh /kaggle/working/outputs.zip
""")

for c in cells:
    if isinstance(c["source"], str):
        lines = c["source"].split("\n")
        c["source"] = [line + "\n" for line in lines[:-1]] + [lines[-1]]
nb = {"cells": cells, "metadata": run5["metadata"], "nbformat": 4, "nbformat_minor": 5}
out_path = HERE / "run7_new_languages.ipynb"
out_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
print("wrote", out_path, len(cells), "cells")
