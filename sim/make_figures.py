"""Generate publication figures from the saved experiment results."""

import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import core

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 200,
})

FIGDIR = "../figs"
import os
os.makedirs(FIGDIR, exist_ok=True)


def load(name):
    with open(name) as fh:
        return json.load(fh)


# ---------------------------------------------------------------- Figure 1
def fig_privacy_utility():
    d = load("results_exp3.json")
    rows = [r for r in d["rows"] if r["eps"] is not None]
    eps = [r["eps"] for r in rows]
    reid = [r["reid_top1"] for r in rows]
    reid5 = [r["reid_top5"] for r in rows]
    diag = [r["diag"] for r in rows]
    nonoise = [r for r in d["rows"] if r["eps"] is None][0]
    chance = d["chance_top1"]

    fig, ax = plt.subplots(figsize=(5.0, 3.3))
    ax.semilogx(eps, diag, "o-", color="#1f77b4", lw=1.8, ms=4.5,
                label="Diagnostic accuracy")
    ax.semilogx(eps, reid, "s-", color="#d62728", lw=1.8, ms=4.5,
                label="Re-identification (top-1)")
    ax.semilogx(eps, reid5, "^--", color="#ff7f0e", lw=1.4, ms=4,
                label="Re-identification (top-5)")
    ax.axhline(chance, color="#d62728", ls=":", lw=1.2)
    ax.text(52, chance + 0.015, "linkage chance", fontsize=6.8, color="#d62728",
            ha="right")
    ax.axhline(0.5, color="#1f77b4", ls=":", lw=1.2)
    ax.text(52, 0.515, "diagnostic chance", fontsize=6.8, color="#1f77b4", ha="right")
    ax.axhline(nonoise["reid_top1"], color="#8c564b", ls="-.", lw=1.2)
    ax.text(0.105, nonoise["reid_top1"] + 0.025,
            "no mechanism: %.0f%% top-1" % (100 * nonoise["reid_top1"]),
            fontsize=6.8, color="#8c564b")
    ax.axvspan(1.0, 2.0, color="green", alpha=0.10)
    ax.text(1.35, 0.30, "operating\nwindow", fontsize=7, ha="center", color="green")
    ax.set_xlabel(r"privacy budget $\varepsilon$")
    ax.set_ylabel("accuracy")
    ax.set_ylim(-0.02, 1.05)
    ax.legend(fontsize=7.5, loc="upper left", framealpha=0.95)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/fig_privacy_utility.pdf")
    fig.savefig(f"{FIGDIR}/fig_privacy_utility.png")
    plt.close(fig)
    print("wrote fig_privacy_utility")


# ---------------------------------------------------------------- Figure 2
def fig_lemma_a():
    eps = np.logspace(-3, 0.5, 300)
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    for R, lab, c in [(2, r"cohort, $R=2$", "#2ca02c"),
                      (20, r"$R=20$", "#1f77b4"),
                      (200, r"small region, $R=200$", "#ff7f0e"),
                      (10000, r"whole slide, $R=10^4$", "#d62728")]:
        ax.semilogx(eps, np.tanh(R * eps / 2), lw=1.8, label=lab, color=c)
    ax.axhline(1.0, color="k", ls=":", lw=1.0)
    ax.set_xlabel(r"privacy budget $\varepsilon$")
    ax.set_ylabel(r"contraction factor $\tanh(R\varepsilon/2)$")
    ax.set_ylim(-0.03, 1.08)
    ax.legend(fontsize=7.5, loc="lower right")
    ax.text(1.2e-3, 0.90, "no contraction:\nbound is vacuous", fontsize=7, color="#d62728")
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/fig_lemma_a.pdf")
    fig.savefig(f"{FIGDIR}/fig_lemma_a.png")
    plt.close(fig)
    print("wrote fig_lemma_a")


# ---------------------------------------------------------------- Figure 3
def fig_ceiling():
    res = [256, 512, 1024, 2048, 4096]
    img = [core.image_entropy_bits(r, r, 3) for r in res]
    ceil_ = [core.structural_ceiling_bits(5000, 35, 8)] * len(res)
    x = np.arange(len(res))
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    ax.bar(x - 0.19, img, 0.38, label="image entropy $H(I)$", color="#d62728")
    ax.bar(x + 0.19, ceil_, 0.38,
           label=r"structural ceiling $\mathcal{C}(n,D,q)$", color="#2ca02c")
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([f"${r}^2$" for r in res])
    ax.set_xlabel("image resolution (3 channels, 8 bits)")
    ax.set_ylabel("bits (log scale)")
    ax.legend(fontsize=7.5, loc="upper left")
    for i, (a, b) in enumerate(zip(img, ceil_)):
        ax.text(i, a * 1.5, r"$%.0f\times$" % (a / b), ha="center", fontsize=7)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/fig_ceiling.pdf")
    fig.savefig(f"{FIGDIR}/fig_ceiling.png")
    plt.close(fig)
    print("wrote fig_ceiling")


# ---------------------------------------------------------------- Figure 4
def fig_sensitivity_tightness():
    d = load("results_exp1.json")["random_family"]
    keys = ["edge_count", "degree_hist", "triangles", "attr_hist", "spectrum_l2"]
    labels = ["edge\ncount", "degree\nhistogram", "triangle\ncount",
              "attribute\nhistogram", "Laplacian\nspectrum"]
    tight = [d[k]["max_tightness_vs_Dmax"] for k in keys]
    fig, ax = plt.subplots(figsize=(5.0, 2.9))
    cols = ["#2ca02c" if t > 0.95 else "#1f77b4" for t in tight]
    ax.bar(labels, tight, color=cols, width=0.6)
    ax.axhline(1.0, color="k", ls="--", lw=1.2)
    ax.text(4.35, 1.02, "bound attained", fontsize=7, ha="right")
    ax.set_ylabel("realised / certified sensitivity")
    ax.set_ylim(0, 1.18)
    for i, t in enumerate(tight):
        ax.text(i, t + 0.03, "%.2f" % t, ha="center", fontsize=7.5)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/fig_sensitivity.pdf")
    fig.savefig(f"{FIGDIR}/fig_sensitivity.png")
    plt.close(fig)
    print("wrote fig_sensitivity")


# ---------------------------------------------------------------- Figure 5
def fig_pareto():
    d = load("results_exp4.json")["pareto"]
    m = [r["m"] for r in d]
    ratio = [r["threshold_ratio"] for r in d]
    labels = [r["resolution"].replace("x3", "") for r in d]
    fig, ax = plt.subplots(figsize=(5.0, 2.9))
    ax.loglog(m, ratio, "o-", color="#1f77b4", lw=1.8, ms=5)
    ref = np.array(m, dtype=float)
    ax.loglog(ref, ref / ref[0] * ratio[0], "k--", lw=1.0, label=r"$\Theta(m)$ reference")
    for xi, yi, li in zip(m, ratio, labels):
        ax.annotate(li, (xi, yi), textcoords="offset points", xytext=(6, -10), fontsize=7)
    ax.set_xlabel("pixel count $m = HWC$")
    ax.set_ylabel(r"$\varepsilon_{\min}^{\rm pixel}/\varepsilon_{\min}^{\rm graph}$")
    ax.legend(fontsize=7.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/fig_pareto.pdf")
    fig.savefig(f"{FIGDIR}/fig_pareto.png")
    plt.close(fig)
    print("wrote fig_pareto")


if __name__ == "__main__":
    fig_privacy_utility()
    fig_lemma_a()
    fig_ceiling()
    fig_sensitivity_tightness()
    fig_pareto()
    print("all figures written to", FIGDIR)
