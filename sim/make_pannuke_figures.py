"""Figures for PanNuke Phase-1 working factors."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figs"
SIM = Path(__file__).resolve().parent
FIG.mkdir(exist_ok=True)

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 9,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 200,
    }
)


def fig_pannuke_privacy_utility():
    d = json.load(open(SIM / "results_pannuke_c.json"))
    rows = [r for r in d["rows"] if r["eps"] is not None]
    none = [r for r in d["rows"] if r["eps"] is None][0]
    eps = [r["eps"] for r in rows]
    reid = [r["reid_top1"] for r in rows]
    reid5 = [r["reid_top5"] for r in rows]
    diag = [r["diag_neoplastic"] for r in rows]
    chance = d["chance_top1"]

    fig, ax = plt.subplots(figsize=(5.0, 3.3))
    ax.semilogx(eps, diag, "o-", color="#1f77b4", lw=1.8, ms=4.5, label="Diagnostic (neoplastic burden)")
    ax.semilogx(eps, reid, "s-", color="#d62728", lw=1.8, ms=4.5, label="Re-identification (top-1)")
    ax.semilogx(eps, reid5, "^--", color="#ff7f0e", lw=1.4, ms=4, label="Re-identification (top-5)")
    ax.axhline(0.5, color="#1f77b4", ls=":", lw=1.1)
    ax.axhline(chance, color="#d62728", ls=":", lw=1.1)
    ax.axhline(none["reid_top1"], color="#8c564b", ls="-.", lw=1.2)
    ax.text(0.12, none["reid_top1"] + 0.02, "no mechanism: %.0f%% top-1" % (100 * none["reid_top1"]),
            fontsize=6.8, color="#8c564b")
    ax.axvspan(5.0, 10.0, color="green", alpha=0.12)
    ax.text(7.0, 0.35, "operating\nwindow", fontsize=7, ha="center", color="green")
    ax.set_xlabel(r"privacy budget $\varepsilon$")
    ax.set_ylabel("accuracy")
    ax.set_ylim(-0.02, 1.05)
    ax.legend(fontsize=7.2, loc="upper left")
    ax.set_title("PanNuke cell graphs (real nuclei)")
    fig.tight_layout()
    fig.savefig(FIG / "fig_pannuke_privacy_utility.pdf")
    fig.savefig(FIG / "fig_pannuke_privacy_utility.png")
    plt.close(fig)
    print("wrote fig_pannuke_privacy_utility")


def fig_pannuke_geometry():
    d = json.load(open(SIM / "results_pannuke_ab.json"))["geometry"]
    labels = ["assumed\n$r_{min}=6$", "emp. p50\nNN", "emp. p05\nNN", "emp. p01\nNN"]
    vals = [6.0, d["nn_p50_um"], d["nn_p05_um"], d["nn_p01_um"]]
    fig, ax = plt.subplots(figsize=(4.6, 2.8))
    ax.bar(labels, vals, color=["#2ca02c", "#1f77b4", "#ff7f0e", "#d62728"], width=0.65)
    ax.set_ylabel(r"distance ($\mu$m)")
    ax.set_title("Nuclear separation on PanNuke")
    for i, v in enumerate(vals):
        ax.text(i, v + 0.15, f"{v:.2f}", ha="center", fontsize=7.5)
    fig.tight_layout()
    fig.savefig(FIG / "fig_pannuke_geometry.pdf")
    fig.savefig(FIG / "fig_pannuke_geometry.png")
    plt.close(fig)
    print("wrote fig_pannuke_geometry")


if __name__ == "__main__":
    fig_pannuke_privacy_utility()
    fig_pannuke_geometry()
