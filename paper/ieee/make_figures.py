#!/usr/bin/env python3
"""Build the paper's figures (vector PDF) from the result files in backend/results/.

    backend/.venv/bin/python paper/ieee/make_figures.py

Colours: validated categorical palette, one fixed slot per system (base = blue, distilled on
raw drafts = orange, terminology-aware = aqua, teacher = yellow). Hatching is added as a
secondary encoding so the figures stay readable in grayscale print.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D, ScaledTranslation

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "backend" / "results"
MODELS = ROOT / "backend" / "models"
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

LANGS = ["hin_Deva", "gom_Deva", "mai_Deva", "doi_Deva"]
LANG_NAME = {"hin_Deva": "Hindi", "gom_Deva": "Konkani", "mai_Deva": "Maithili", "doi_Deva": "Dogri"}
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, GRID = "#1a1a1a", "#52514e", "#e1e0d9"

plt.rcParams.update({
    "font.family": "Nimbus Roman",
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.edgecolor": INK2,
    "axes.linewidth": 0.6,
    "xtick.color": INK2,
    "ytick.color": INK2,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "hatch.linewidth": 0.5,
    "pdf.fonttype": 42,  # embed TrueType (IEEE PDF eXpress requires embedded fonts)
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})
COL = 3.45  # IEEE single-column width (in)


def style(ax, ygrid=True):
    ax.spines[["top", "right"]].set_visible(False)
    if ygrid:
        ax.yaxis.grid(True, color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)


def text_as_path(ax, x, y, s, size, color):
    """Draw s centred at data point (x, y) as a filled outline (size in points)."""
    prop = FontProperties(family=plt.rcParams["font.family"])
    tp = TextPath((0, 0), s, size=size, prop=prop)
    bb = tp.get_extents()
    # Centre vertically on the "lp" line box, as matplotlib does for va="center" text,
    # so the outlines line up with the ordinary text labels.
    ref = TextPath((0, 0), "lp", size=size, prop=prop).get_extents()
    cy = (ref.y0 + max(ref.y1, bb.y1)) / 2
    trans = (
        Affine2D().translate(-(bb.x0 + bb.width / 2), -cy).scale(1 / 72)
        + ax.figure.dpi_scale_trans
        + ScaledTranslation(x, y, ax.transData)
    )
    ax.add_patch(PathPatch(tp, transform=trans, facecolor=color, edgecolor="none", zorder=3))


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=220)
    plt.close(fig)
    print("wrote", OUT / f"{name}.pdf")


# --------------------------------------------------------------------------- data
macro = pd.read_csv(RESULTS / "term_compliance_macro.csv")
scores = pd.read_csv(RESULTS / "domain_scores_UNVERIFIED_run6_all.csv")


def macro_of(system, lang):
    return float(macro[(macro.system == system) & (macro.target_lang == lang)].macro.iloc[0])


def chrf_of(system, lang):
    return float(scores[(scores.system == system) & (scores.target_lang == lang)].chrf_pp.iloc[0])


# ---------------------------------------------------------- Fig. 2: teacher consistency heatmap
def fig_teacher_heatmap():
    t = pd.read_csv(RESULTS / "teacher_term_consistency.csv")
    t = t[t.target_lang.isin(LANGS)]
    n = t.groupby("english_term").sentences.max()
    terms = n[n >= 30].sort_values(ascending=False).index.tolist()
    piv = t.pivot(index="english_term", columns="target_lang", values="teacher_uses_glossary_pct").loc[terms, LANGS]
    fig, ax = plt.subplots(figsize=(COL, 2.85))
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("seq", ["#f4f8fd", "#9ec5f4", "#3987e5", "#184f95"])
    ax.imshow(piv.values, cmap=cmap, vmin=0, vmax=100, aspect="auto")
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            if v > 60:
                # White labels are drawn as outlines, not text: white text in a PDF is
                # reported as "hidden text" by plagiarism checkers (Turnitin).
                text_as_path(ax, j, i, f"{v:.0f}", 6.5, "white")
            else:
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.5, color=INK)
    ax.set_xticks(range(len(LANGS)), [LANG_NAME[l] for l in LANGS])
    ax.set_yticks(range(len(terms)), [f"{x} ({n[x]})" for x in terms])
    ax.tick_params(length=0)
    ax.xaxis.tick_top()
    for s in ax.spines.values():
        s.set_visible(False)
    save(fig, "fig_teacher_consistency")


# ---------------------------------------------------------- Fig. 3: macro compliance by language
def fig_compliance():
    systems = [
        ("base", "Base (dist-200M)", BLUE, ""),
        ("lora", "Distilled, raw drafts", ORANGE, "////"),
        ("formal", "Terminology-aware (ours)", AQUA, "...."),
        ("teacher", "Teacher (1B)", YELLOW, "xxxx"),
    ]
    x = np.arange(len(LANGS))
    w = 0.2
    fig, ax = plt.subplots(figsize=(COL, 2.05))
    for k, (key, label, color, hatch) in enumerate(systems):
        if key == "formal":
            a = np.array([macro_of("lora_joint_formal_v2", l) for l in LANGS])
            b = np.array([macro_of("lora_joint_formal_v2_s43", l) for l in LANGS])
            vals = (a + b) / 2
            err = np.vstack([vals - np.minimum(a, b), np.maximum(a, b) - vals])
        else:
            vals, err = np.array([macro_of(key, l) for l in LANGS]), None
        pos = x + (k - 1.5) * w
        ax.bar(pos, vals, w * 0.92, color=color, edgecolor="white", linewidth=0.4, hatch=hatch, label=label, zorder=2)
        if err is not None:
            ax.errorbar(pos, vals, yerr=err, fmt="none", ecolor=INK, elinewidth=0.6, capsize=1.5, zorder=3)
            for p, v in zip(pos, vals):
                ax.text(p, v + 3, f"{v:.0f}", ha="center", va="bottom", fontsize=6, color=INK)
    ax.set_xticks(x, [LANG_NAME[l] for l in LANGS])
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("Formal-term use, macro (%)")
    style(ax)
    ax.legend(ncol=2, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.28), handlelength=1.4, columnspacing=1.0)
    save(fig, "fig_compliance")


# ---------------------------------------------------------- Fig. 4: enforcement trade-off
def fig_tradeoff():
    """Two-panel dot plot: term use (left) and chrF++ against teacher drafts (right), one row per
    configuration, mean over the four languages."""
    rows = [
        ("base", "Base", BLUE, "o"),
        ("base+ph", "Base + placeholders", BLUE, "^"),
        ("base+cd", "Base + constrained dec.", BLUE, "s"),
        ("lora_formal", "Term-aware (r5)", AQUA, "o"),
        ("lora_formal+ph", "r5 + placeholders", AQUA, "^"),
        ("lora_formal+cd", "r5 + constrained dec.", AQUA, "s"),
        ("lora_formal+hy", "r5 + hybrid", AQUA, "D"),
        ("lora_joint_formal_v2", "Term-aware (r6)", "#0d7a52", "o"),
        ("lora_joint_formal_v2+hy", "r6 + hybrid", "#0d7a52", "D"),
    ]
    y = np.arange(len(rows))[::-1]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(COL, 2.35), sharey=True, gridspec_kw={"wspace": 0.08})
    for yi, (key, label, color, marker) in zip(y, rows):
        comp = np.mean([macro_of(key, l) for l in LANGS])
        chrf = np.mean([chrf_of(key, l) for l in LANGS])
        for ax, v, fmt in [(a1, comp, "{:.0f}"), (a2, chrf, "{:.1f}")]:
            ax.scatter(v, yi, s=24, color=color, marker=marker, edgecolor="white", linewidth=0.5, zorder=3)
            ax.text(v + (1.6 if ax is a1 else 0.5), yi, fmt.format(v), va="center", fontsize=6, color=INK2)
    for yi in (y[3] + 0.5, y[7] + 0.5):  # separators between model families
        for ax in (a1, a2):
            ax.axhline(yi, color=GRID, linewidth=0.8)
    a1.set_yticks(y, [r[1] for r in rows])
    a1.set_xlim(30, 112)
    a1.set_xticks([40, 60, 80, 100])
    a1.set_xlabel("Formal-term use, macro (%)")
    a2.set_xlim(65, 81)
    a2.set_xticks([66, 70, 74, 78])
    a2.set_xlabel("chrF++ vs teacher drafts")
    for ax in (a1, a2):
        ax.spines[["top", "right"]].set_visible(False)
        ax.xaxis.grid(True, color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", length=0)
    save(fig, "fig_tradeoff")


# ---------------------------------------------------------- Fig. 5: dev curves
def fig_dev_curves():
    runs = [
        ("it2_lora_joint", "Run 4, raw drafts", ORANGE, "-"),
        ("it2_lora_joint_formal", "Run 5, repaired", AQUA, "--"),
        ("it2_lora_joint_formal_v2", "Run 6, seed 42", "#0d7a52", "-"),
        ("it2_lora_joint_formal_v2_s43", "Run 6, seed 43", "#0d7a52", ":"),
    ]
    fig, ax = plt.subplots(figsize=(COL, 1.85))
    for run, label, color, ls in runs:
        meta = json.loads((MODELS / run / "training_metadata.json").read_text())
        pts = [(e["step"], e["eval_chrF++"]) for e in meta["log_history"] if "eval_chrF++" in e]
        pts = sorted(dict(pts).items())
        ax.plot([p[0] for p in pts], [p[1] for p in pts], ls, color=color, linewidth=1.6, label=label, marker="o", markersize=2.5)
    ax.set_xlabel("Training step (effective batch 64)")
    ax.set_ylabel("Dev chrF++")
    style(ax)
    ax.legend(frameon=False, ncol=2, loc="lower right", handlelength=2.2)
    save(fig, "fig_dev_curves")


# ---------------------------------------------------------- Fig. 6: IN22-Gen base, 22 languages
def fig_in22():
    d = pd.read_csv(RESULTS / "in22_gen_scores.csv")
    d = d[d.system == "base"].sort_values("chrf_pp")
    fig, ax = plt.subplots(figsize=(COL, 2.7))
    colors = [BLUE] * len(d)  # all bars are the base model; domain languages marked by hatching only
    hatches = ["...." if c in LANGS else "" for c in d.language_code]
    bars = ax.barh(range(len(d)), d.chrf_pp, height=0.72, color=colors, edgecolor="white", linewidth=0.4, zorder=2)
    for b, h in zip(bars, hatches):
        b.set_hatch(h)
    for i, (v, b) in enumerate(zip(d.chrf_pp, d.bleu)):
        ax.text(v + 0.8, i, f"{v:.1f}", va="center", fontsize=6, color=INK2)
    ax.set_yticks(range(len(d)), [f"{n}*" if c in LANGS else n for n, c in zip(d.language_name, d.language_code)])
    ax.set_xlim(0, 75)
    ax.set_xlabel("chrF++ on IN22-Gen (English to X)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    save(fig, "fig_in22")


if __name__ == "__main__":
    fig_teacher_heatmap()
    fig_compliance()
    fig_tradeoff()
    fig_dev_curves()
    fig_in22()
