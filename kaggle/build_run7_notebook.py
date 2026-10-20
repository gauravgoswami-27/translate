#!/usr/bin/env python3
"""Generate kaggle/run7_seed_rank.ipynb (reuses the setup cells of the run-5 notebook).

Run 7 = robustness extras on the run-6 setup (case-fixed formal drafts):
  GPU 0: third seed of the main joint model (seed 44)          -> 3-seed mean / spread
  GPU 1: LoRA rank sweep r = 4, 8, 32, 64 on Hindi-only       -> rank ablation (r=16 exists from run 6)
         (alpha = 2r so the LoRA scaling alpha/r stays 2, as in r=16/alpha=32)

    python3 kaggle/build_run7_notebook.py
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
run5 = json.loads((HERE / "run5_terminology_aware.ipynb").read_text())
setup_cells = run5["cells"][1:4]  # copy stamped bundle, pinned install, HF token + access check
RANKS = [4, 8, 32, 64]

cells = []


def md(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": text.strip("\n")})


def code(text):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text.strip("\n")})


md(f"""
# Vocational NMT: run 7, third seed + LoRA rank sweep

Same data as run 6 (case-fixed formal drafts, shipped in the bundle); no translation of training data.

**GPU 0:** `joint_formal_v2_s44`, the main joint model with seed 44 → domain evaluation (plain and hybrid). With seeds 42 and 43 from run 6, this gives a 3-seed mean and spread.
**GPU 1:** Hindi-only LoRA rank sweep r = {", ".join(map(str, RANKS))} (alpha = 2r; r = 16 exists from run 6) → Hindi evaluation of each.

**Input:** only the latest bundle dataset. Use GPU T4 x2, Internet on, and the `HF_TOKEN` secret. Then **Save & Run All** (about 2.5 hours); the outputs end up in `/kaggle/working/outputs.zip`.
""")
cells.extend(setup_cells)
code("""
# 4. Smoke test (~3 min): 10 training steps at the smallest rank, then load the adapter
def check(step):
    assert _exit_code == 0, f"{step} failed - see the output above"

for s in ["hi", "gom", "mai", "doi"]:
    assert (CORPUS / f"drafts_{s}_formal.csv").exists(), f"drafts_{s}_formal.csv missing from the bundle"
!CUDA_VISIBLE_DEVICES=0 python -m backend.finetune --drafts-variant formal --langs hin_Deva --lora-r 4 --lora-alpha 8 --run-name smoke --max-steps 10 --eval-steps 5 --dev-per-lang 8
check("training smoke test")
!python -m backend.baseline_inference --model backend/models/it2_lora_smoke --text "Test the insulation with a megger." --target-lang hin_Deva
check("adapter loading")
shutil.rmtree("backend/models/it2_lora_smoke", ignore_errors=True)
""")
md("## Training: GPU 0 third seed, GPU 1 rank sweep (each rank trained, then evaluated)")
sweep = " && ".join(
    f"python -m backend.finetune --drafts-variant formal --langs hin_Deva --lora-r {r} --lora-alpha {2 * r} --run-name hi_formal_v2_r{r} && "
    f"python -m backend.run_domain_eval --langs hin_Deva --systems lora_hi_formal_v2_r{r} --tag run7_r{r}"
    for r in RANKS
)
code(f"""
import torch
n_gpu = torch.cuda.device_count()
gpu1 = None
sweep = {sweep!r}
if n_gpu >= 2:
    gpu1 = subprocess.Popen(["bash", "-c", sweep], env=dict(os.environ, CUDA_VISIBLE_DEVICES="1"),
                            stdout=open("/kaggle/working/rank_sweep_gpu1.log", "w"), stderr=subprocess.STDOUT)
else:
    print("Only one GPU: the rank sweep runs after the seed-44 model.")

!CUDA_VISIBLE_DEVICES=0 python -m backend.finetune --drafts-variant formal --run-name joint_formal_v2_s44 --seed 44
check("seed-44 fine-tuning")
!CUDA_VISIBLE_DEVICES=0 python -m backend.run_domain_eval --systems lora_joint_formal_v2_s44,lora_joint_formal_v2_s44+hy --tag run7_s44
check("seed-44 evaluation")

if gpu1 is not None:
    print("rank sweep exit code:", gpu1.wait())
    print(open("/kaggle/working/rank_sweep_gpu1.log").read()[-3000:])
else:
    !CUDA_VISIBLE_DEVICES=0 bash -c {sweep!r}
""")
code("""
# Package everything that must come back to your machine
out = Path("/kaggle/working/outputs")
shutil.rmtree(out, ignore_errors=True)
out.mkdir(parents=True)
for src in sorted(Path("backend/models").glob("it2_lora_*")):
    if src.name in {"it2_lora_joint"}:  # shipped in the bundle, not produced here
        continue
    shutil.copytree(src, out / src.name, ignore=shutil.ignore_patterns("checkpoints"))
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
out_path = HERE / "run7_seed_rank.ipynb"
out_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False))
print("wrote", out_path, len(cells), "cells")
