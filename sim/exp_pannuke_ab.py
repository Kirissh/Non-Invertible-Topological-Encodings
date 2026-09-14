"""
PanNuke Experiment A+B: geometry packing bound and sensitivity working factors.
"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import numpy as np

import core
import pannuke_load as pl

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
FIG = ROOT / "figs"
FIG.mkdir(exist_ok=True)

# Graph construction parameters (micrometres)
R = 15.0
R_MIN_ASSUMED = 6.0
D_TRUNC = 35
Q = 5


def nn_distances(pts: np.ndarray) -> np.ndarray:
    if len(pts) < 2:
        return np.array([])
    d = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=-1)
    np.fill_diagonal(d, np.inf)
    return d.min(axis=1)


def exact_sens_edge(G):
    base = G.number_of_edges()
    worst = 0
    for v in list(G.nodes()):
        H = G.copy()
        H.remove_node(v)
        worst = max(worst, abs(base - H.number_of_edges()))
    return worst


def exact_sens_hist(G, D):
    base = core.q_degree_hist(G, D=D)
    worst = 0.0
    for v in list(G.nodes()):
        H = G.copy()
        H.remove_node(v)
        H = nx.convert_node_labels_to_integers(H)
        val = core.q_degree_hist(H, D=D)
        worst = max(worst, float(np.abs(base - val).sum()))
    return worst


def exact_sens_attr(G, q=Q):
    base = core.q_attr_hist(G, q=q)
    worst = 0.0
    for v in list(G.nodes()):
        H = G.copy()
        H.remove_node(v)
        H = nx.convert_node_labels_to_integers(H)
        for i in H.nodes():
            if "x" not in H.nodes[i]:
                H.nodes[i]["x"] = 0
        val = core.q_attr_hist(H, q=q)
        # pad
        a = np.zeros(q); a[: len(base)] = base
        b = np.zeros(q); b[: len(val)] = val
        worst = max(worst, float(np.abs(a - b).sum()))
    return worst


def exact_sens_spec_l2(G):
    n = G.number_of_nodes()
    base = core.laplacian_spectrum_padded(G, n)
    worst = 0.0
    for v in list(G.nodes()):
        H = G.copy()
        H.remove_node(v)
        val = core.laplacian_spectrum_padded(H, n)
        worst = max(worst, float(np.linalg.norm(base - val)))
    return worst


def run(max_patches=400, seed=14):
    rng = np.random.default_rng(seed)
    cache = pl.DATA_DIR / "processed_cells.npz"
    if cache.exists():
        rows = pl.load_compact_cache()
    else:
        rows = pl.load_pannuke(max_samples=1200, prefer="hf")
        pl.save_compact_cache(rows)

    # subsample for expensive exact sensitivity
    idx = rng.choice(len(rows), size=min(max_patches, len(rows)), replace=False)
    sample = [rows[i] for i in idx]

    nn_all = []
    deg_obs = []
    pack_ok = 0
    graphs_built = 0
    sens_rows = []

    D_pack = (1 + 2 * R / R_MIN_ASSUMED) ** 2 - 1

    for r in sample:
        pts = r["points_um"]
        attrs = r["attrs"]
        nn = nn_distances(pts)
        if nn.size:
            nn_all.append(nn)
        G_raw = core.radius_graph(pts, R)
        for i in G_raw.nodes():
            G_raw.nodes[i]["x"] = int(attrs[i]) if i < len(attrs) else 0
        if G_raw.number_of_nodes() < 8:
            continue
        graphs_built += 1
        dmax_raw = max(d for _, d in G_raw.degree()) if G_raw.number_of_edges() or G_raw.number_of_nodes() else 0
        if G_raw.number_of_nodes():
            dmax_raw = max((d for _, d in G_raw.degree()), default=0)
        deg_obs.append(dmax_raw)
        if dmax_raw <= D_pack + 1e-9:
            pack_ok += 1

        G = core.truncate_degree(G_raw, D_TRUNC)

        # sensitivity on a subset (first 120 graphs) — exact enumeration
        if len(sens_rows) < 120 and G.number_of_nodes() <= 80:
            Dmax = max((d for _, d in G.degree()), default=0)
            se = exact_sens_edge(G)
            sh = exact_sens_hist(G, D=D_TRUNC)
            sa = exact_sens_attr(G)
            ss = exact_sens_spec_l2(G)
            sens_rows.append(
                {
                    "n": G.number_of_nodes(),
                    "Dmax": Dmax,
                    "edge": se,
                    "edge_bound": 1 * D_TRUNC,
                    "hist": sh,
                    "hist_bound": 1 * (2 * D_TRUNC + 1),
                    "attr": sa,
                    "attr_bound": 1.0,
                    "spec_l2": ss,
                    "spec_bound": float(core.bound_spectrum_l2(1, D_TRUNC)),
                    "spec_bound_Dmax": float(core.bound_spectrum_l2(1, Dmax)),
                }
            )

    nn_cat = np.concatenate(nn_all) if nn_all else np.array([np.nan])
    geom = {
        "n_patches": graphs_built,
        "r_um": R,
        "r_min_assumed_um": R_MIN_ASSUMED,
        "D_pack": float(D_pack),
        "nn_p01_um": float(np.nanpercentile(nn_cat, 1)),
        "nn_p05_um": float(np.nanpercentile(nn_cat, 5)),
        "nn_p50_um": float(np.nanpercentile(nn_cat, 50)),
        "max_degree_observed": int(max(deg_obs)) if deg_obs else 0,
        "mean_max_degree": float(np.mean(deg_obs)) if deg_obs else 0.0,
        "packing_violations": int(graphs_built - pack_ok),
        "packing_holds": bool(pack_ok == graphs_built),
    }

    def summarize(key, bkey, bkey2=None):
        ex = np.array([s[key] for s in sens_rows], dtype=float)
        bd = np.array([s[bkey] for s in sens_rows], dtype=float)
        viol = int((ex > bd + 1e-6).sum())
        out = {
            "n": len(ex),
            "max_exact": float(ex.max()) if len(ex) else 0,
            "bound": float(bd[0]) if len(bd) else 0,
            "violations_vs_D": viol,
            "max_tightness": float((ex / np.maximum(bd, 1e-12)).max()) if len(ex) else 0,
        }
        if bkey2:
            bd2 = np.array([s[bkey2] for s in sens_rows], dtype=float)
            out["violations_vs_Dmax"] = int((ex > bd2 + 1e-6).sum())
            out["max_tightness_Dmax"] = float(
                (ex / np.maximum(bd2, 1e-12)).max()
            )
        return out

    sens = {
        "edge_count": summarize("edge", "edge_bound"),
        "degree_hist": summarize("hist", "hist_bound"),
        "attr_hist": summarize("attr", "attr_bound"),
        "spectrum_l2": summarize("spec_l2", "spec_bound", "spec_bound_Dmax"),
    }

    results = {"geometry": geom, "sensitivity": sens, "n_sens_graphs": len(sens_rows)}
    with open(OUT / "results_pannuke_ab.json", "w") as fh:
        json.dump(results, fh, indent=2)

    print("=" * 72)
    print("PANNUKE GEOMETRY")
    print("=" * 72)
    for k, v in geom.items():
        print(f"  {k}: {v}")
    print("=" * 72)
    print("PANNUKE SENSITIVITY")
    print("=" * 72)
    for name, s in sens.items():
        print(
            f"  {name}: max_exact={s['max_exact']:.3f} bound={s['bound']:.3f} "
            f"violations={s['violations_vs_D']} tightness={s['max_tightness']:.3f}"
        )
    print("saved results_pannuke_ab.json")
    return results


if __name__ == "__main__":
    run()
