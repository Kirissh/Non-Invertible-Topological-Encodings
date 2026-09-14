"""
PanNuke Experiment C: two-view re-identification vs diagnostic utility under DP.

Diagnostic task: neoplastic-rich vs not (fraction of neoplastic nuclei >= median),
or multi-class tissue when enough samples — we use binary neoplastic burden for
stable accuracy on graph summaries.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder

import core
import pannuke_load as pl

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
FIG = ROOT / "figs"

R = 15.0
D = 12  # truncation near observed max degrees on PanNuke
Q = 5
P_SPEC = 4


def features(G):
    return np.concatenate(
        [
            core.q_degree_hist(G, D=D),
            core.q_attr_hist(G, q=Q),
            core.q_spectrum(G, p=P_SPEC, n_pad=max(G.number_of_nodes(), P_SPEC)),
        ]
    )


def sensitivity_cell(s=1):
    return (
        core.bound_degree_hist(s, D)
        + core.bound_attr_hist(s)
        + core.bound_spectrum_l1(s, D, p=P_SPEC)
    )


def acquire(rng, pts, attrs, jitter=1.2, keep=0.88, attr_flip=0.05):
    keep_mask = rng.random(len(pts)) < keep
    p = pts[keep_mask] + rng.normal(0, jitter, size=(int(keep_mask.sum()), 2))
    a = attrs[keep_mask].copy()
    flip = rng.random(len(a)) < attr_flip
    a[flip] = rng.integers(0, Q, size=int(flip.sum()))
    G = core.build_graph(p, a, r=R, D=D)
    if G.number_of_nodes() < 5:
        return None
    return features(G)


def reid_topk(gallery, probes, k=1):
    mu, sd = gallery.mean(0), gallery.std(0) + 1e-9
    Gz = (gallery - mu) / sd
    Pz = (probes - mu) / sd
    d = np.linalg.norm(Pz[:, None, :] - Gz[None, :, :], axis=-1)
    order = np.argsort(d, axis=1)[:, :k]
    truth = np.arange(len(probes))[:, None]
    return float((order == truth).any(axis=1).mean())


def diag_acc(Xtr, ytr, Xte, yte):
    if len(np.unique(ytr)) < 2:
        return float("nan")
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(max_iter=4000, C=1.0)
    clf.fit(sc.transform(Xtr), ytr)
    return float(clf.score(sc.transform(Xte), yte))


def run(n_patients=400, seed=21, n_repeats=4):
    rng = np.random.default_rng(seed)
    cache = pl.DATA_DIR / "processed_cells.npz"
    if cache.exists():
        rows = pl.load_compact_cache()
    else:
        rows = pl.load_pannuke(max_samples=1500, prefer="hf")
        pl.save_compact_cache(rows)

    # keep reasonably sized graphs
    rows = [r for r in rows if 15 <= r["n_cells"] <= 120]
    idx = rng.choice(len(rows), size=min(n_patients, len(rows)), replace=False)
    cohort = [rows[i] for i in idx]

    A, B, y_neo, tissues = [], [], [], []
    for r in cohort:
        fa = acquire(rng, r["points_um"], r["attrs"])
        fb = acquire(rng, r["points_um"], r["attrs"])
        if fa is None or fb is None:
            continue
        # align dims
        A.append(fa)
        B.append(fb)
        neo_frac = float((r["attrs"] == 0).mean())
        y_neo.append(neo_frac)
        tissues.append(r["tissue"])

    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    # binary diagnostic label: high neoplastic burden
    med = float(np.median(y_neo))
    y = (np.asarray(y_neo) >= med).astype(int)
    n = len(A)
    chance = 1.0 / n
    d_cell = sensitivity_cell()
    print(f"cohort n={n}, feature_dim={A.shape[1]}, sens={d_cell:.2f}, chance={chance:.4f}")
    print(f"neoplastic threshold (median frac)={med:.3f}, class balance={y.mean():.2f}")

    # also tissue multiclass on a subset with enough labels
    le = LabelEncoder()
    yt = le.fit_transform(tissues)

    n_tr = n // 2
    eps_grid = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0, None]
    rows_out = []
    for eps in eps_grid:
        r1, r5, dg, dt = [], [], [], []
        for _ in range(n_repeats):
            Bn = B.copy() if eps is None else core.laplace_mechanism(rng, B, d_cell, eps)
            r1.append(reid_topk(A, Bn, k=1))
            r5.append(reid_topk(A, Bn, k=5))
            dg.append(diag_acc(Bn[:n_tr], y[:n_tr], Bn[n_tr:], y[n_tr:]))
            # tissue: may be hard; still report
            dt.append(diag_acc(Bn[:n_tr], yt[:n_tr], Bn[n_tr:], yt[n_tr:]))
        rows_out.append(
            {
                "eps": eps,
                "reid_top1": float(np.mean(r1)),
                "reid_top5": float(np.mean(r5)),
                "diag_neoplastic": float(np.nanmean(dg)),
                "diag_tissue": float(np.nanmean(dt)),
                "reid_lift": float(np.mean(r1) / chance),
            }
        )

    print("=" * 84)
    print("PANNUKE TWO-VIEW RE-ID vs UTILITY")
    print("=" * 84)
    print(
        f"{'eps':>8} | {'top1':>8} {'top5':>8} {'lift':>8} | {'neo':>8} {'tissue':>8}"
    )
    print("-" * 84)
    for r in rows_out:
        e = "none" if r["eps"] is None else f"{r['eps']:.2f}"
        print(
            f"{e:>8} | {r['reid_top1']:8.4f} {r['reid_top5']:8.4f} {r['reid_lift']:8.1f} | "
            f"{r['diag_neoplastic']:8.4f} {r['diag_tissue']:8.4f}"
        )

    out = {
        "n": n,
        "chance_top1": chance,
        "sensitivity_cell": d_cell,
        "feature_dim": int(A.shape[1]),
        "neoplastic_median": med,
        "rows": rows_out,
        "n_tissue_classes": int(len(le.classes_)),
    }
    with open(OUT / "results_pannuke_c.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved results_pannuke_c.json")
    return out


if __name__ == "__main__":
    run()
