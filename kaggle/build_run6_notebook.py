#!/usr/bin/env python3
"""Generate kaggle/run6_case_fixed.ipynb (reuses the setup cells of the run-5 notebook).

    python3 kaggle/build_run6_notebook.py
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
run5 = json.loads((HERE / "run5_terminology_aware.ipynb").read_text())
setup_cells = run5["cells"][1:4]  # 1: copy stamped bundle, 2: pinned install, 3: HF token + access check

cells = []


def md(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": text.strip("\n")})


def code(text):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text.strip("\n")})


md("""
# Vocational NMT: run 6, terminology-aware distillation on case-fixed drafts

What changed since run 5: Maithili and Konkani case endings that placeholder repair had
detached ("विद्युतरोधन क") are re-attached in the repaired training drafts (1,050 mai and 427 gom rows).
The repaired drafts ship in the bundle, so this notebook does no translation of training data.

**GPU 0:** `joint_formal_v2` (seed 42), the main run 6 model → domain evaluation (plain and hybrid) → IN22-Gen forgetting check.
**GPU 1, in parallel:** `joint_formal_v2_s43` (seed 43, for seed variance) → `hi_formal_v2` (Hindi only, for the joint-vs-single ablation) → their evaluations.

**Input:** only the latest bundle dataset. Use GPU T4 x2, Internet on, and the `HF_TOKEN` secret. Then **Save & Run All** (about 3 hours); the outputs end up in `/kaggle/working/outputs.zip`.
""")
cells.extend(setup_cells)
code("""
# 4. Checks + smoke test (~5 min): case-fixed formal drafts present, 10 training steps, adapter loading
def check(step):
    assert _exit_code == 0, f"{step} failed - see the output above"

import re
import pandas as pd
for s in ["hi", "gom", "mai", "doi"]:
    assert (CORPUS / f"drafts_{s}_formal.csv").exists(), f"drafts_{s}_formal.csv missing from the bundle"
mai = pd.read_csv(CORPUS / "drafts_mai_formal.csv", keep_default_na=False)
detached = mai[mai.term_repair == "repaired"].target_sentence.str.contains(r"(?:न|ला|क्ष|र्क) (?:क|केँ|सँ|मे)(?=[\\s।.,])").sum()
print("Maithili repaired drafts with a detached case ending after a term-like word:", detached, "(run 5 data: >1000)")

!CUDA_VISIBLE_DEVICES=0 python -m backend.finetune --drafts-variant formal --run-name smoke --max-steps 10 --eval-steps 5 --dev-per-lang 8
check("training smoke test")
!python -m backend.baseline_inference --model backend/models/it2_lora_smoke --text "Test the insulation with a megger." --target-lang mai_Deva
check("adapter loading")
shutil.rmtree("backend/models/it2_lora_smoke", ignore_errors=True)
""")
md("## Step 1: training (GPU 0: main model; GPU 1: seed 43, then Hindi-only)")
code("""
import torch
n_gpu = torch.cuda.device_count()
gpu1 = None
if n_gpu >= 2:
    chain = ("python -m backend.finetune --drafts-variant formal --run-name joint_formal_v2_s43 --seed 43 && "
             "python -m backend.finetune --drafts-variant formal --run-name hi_formal_v2 --langs hin_Deva")
    gpu1 = subprocess.Popen(["bash", "-c", chain], env=dict(os.environ, CUDA_VISIBLE_DEVICES="1"),
                            stdout=open("/kaggle/working/train_gpu1.log", "w"), stderr=subprocess.STDOUT)
else:
    print("Only one GPU: the seed-43 and Hindi-only runs are skipped.")

!CUDA_VISIBLE_DEVICES=0 python -m backend.finetune --drafts-variant formal --run-name joint_formal_v2
check("main fine-tuning")
""")
md("## Step 2: evaluation")
code("""
!CUDA_VISIBLE_DEVICES=0 python -m backend.run_domain_eval --systems lora_joint_formal_v2,lora_joint_formal_v2+hy --tag run6a
check("evaluation of the main model")

if gpu1 is not None:
    print("GPU 1 training exit code:", gpu1.wait())
    print(open("/kaggle/working/train_gpu1.log").read()[-2500:])
    gpu1_eval = subprocess.Popen(
        ["bash", "-c",
         "python -m backend.run_domain_eval --systems lora_joint_formal_v2_s43,lora_joint_formal_v2_s43+hy --tag run6b && "
         "python -m backend.run_domain_eval --langs hin_Deva --systems lora_hi_formal_v2,lora_hi_formal_v2+hy --tag run6c"],
        env=dict(os.environ, CUDA_VISIBLE_DEVICES="1"),
        stdout=open("/kaggle/working/eval_gpu1.log", "w"), stderr=subprocess.STDOUT)
else:
    gpu1_eval = None

if IN22_OK:
    !CUDA_VISIBLE_DEVICES=0 python -m backend.run_baseline_eval --skip-base --adapter backend/models/it2_lora_joint_formal_v2 --output backend/results/in22_gen_lora_formal_v2.csv
else:
    print("Skipped IN22-Gen: no access.")

if gpu1_eval is not None:
    print("GPU 1 evaluation exit code:", gpu1_eval.wait())
    print(open("/kaggle/working/eval_gpu1.log").read()[-3000:])
""")
code("""
# Package everything that must come back to your machine
out = Path("/kaggle/working/outputs")
shutil.rmtree(out, ignore_errors=True)
out.mkdir(parents=True)
for run in ["joint_formal_v2", "joint_formal_v2_s43", "hi_formal_v2"]:
    src = Path(f"backend/models/it2_lora_{run}")
    if src.exists():
        shutil.copytree(src, out / f"it2_lora_{run}", ignore=shutil.ignore_patterns("checkpoints"))
    else:
        print("missing:", src)
shutil.copytree("backend/results", out / "results")
for log in glob.glob("/kaggle/working/*.log"):
    shutil.copy(log, out)
shutil.make_archive("/kaggle/working/outputs", "zip", out)
!du -sh /kaggle/working/outputs.zip
""")

for c in cells:
    lines = c["source"].split("\n") if isinstance(c["source"], str) else None
    if lines is not None:
        c["source"] = [line + "\n" for line in lines[:-1]] + [lines[-1]]
nb = {"cells": cells, "metadata": run5["metadata"], "nbformat": 4, "nbformat_minor": 5}
out_path = HERE / "run6_case_fixed.ipynb"
out_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
print("wrote", out_path, len(cells), "cells")
