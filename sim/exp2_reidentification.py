"""
Experiment 2: linkage (re-identification) versus reconstruction.

This is the decisive experiment. The paper argues that the topological transform
Phi destroys biometric identity because it is heavily many-to-one. That argument
is sound for RECONSTRUCTION of the image. This experiment tests whether it also
holds for LINKAGE, i.e. deciding which of N enrolled patients produced a release.

Threat model. The adversary holds a gallery of clean topological feature vectors
for N enrolled patients (auxiliary information) and observes one released, noisy
feature vector. It matches by nearest neighbour. Chance accuracy is 1/N.

Two noise calibrations are compared:

  cell-level   sensitivity for removing s cells from the slide, which is what
               Definition 1 with small s prescribes;
  slide-level  sensitivity for replacing the entire slide, which is the unit that
               actually corresponds to "this patient participated".
"""

import json
import numpy as np
import networkx as nx
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import core

D = 8
Q = 4
P_SPEC = 6
R_RADIUS = 15.0
R_MIN = 6.0
N_CELLS = 300
FIELD = 420.0
S_UNIT = 1


def features(G):
    """Concatenated topological summary f(G) consumed by the diagnostic head."""
    return np.concatenate([
        core.q_degree_hist(G, D=D),
        core.q_attr_hist(G, q=Q),
        core.q_spectrum(G, p=P_SPEC, n_pad=max(G.number_of_nodes(), P_SPEC)),
    ])


def sensitivity_cell_level(s=S_UNIT):
    """l1 node sensitivity of the concatenated summary, Propositions 5 and 6."""
    return (core.bound_degree_hist(s, D)
            + core.bound_attr_hist(s)
            + core.bound_spectrum_l1(s, D, p=P_SPEC))


def sensitivity_slide_level(n=N_CELLS):
    """l1 sensitivity when the neighbouring unit is the entire slide.

    Degree and attribute histograms each sum to n, so replacing the slide can move
    each by at most 2n. Laplacian eigenvalues are bounded by 2D, giving 2pD.
    """
    return 2.0 * n + 2.0 * n + 2.0 * P_SPEC * D


def build_cohort(rng, n_patients):
    F, y = [], []
    for i in range(n_patients):
        label = i % 2
        pts, attrs = core.make_patient(rng, label, n_cells=N_CELLS, field=FIELD,
                                       r_min=R_MIN, q=Q, n_clusters=6, spread=30.0)
        G = core.build_graph(pts, attrs, r=R_RADIUS, D=D)
        F.append(features(G))
        y.append(label)
    return np.array(F), np.array(y)


def reid_accuracy(gallery, probes, rng):
    """Top-1 nearest-neighbour linkage accuracy, on z-scored features."""
    mu, sd = gallery.mean(0), gallery.std(0) + 1e-9
    Gz = (gallery - mu) / sd
    Pz = (probes - mu) / sd
    d = np.linalg.norm(Pz[:, None, :] - Gz[None, :, :], axis=-1)
    pred = d.argmin(axis=1)
    return float((pred == np.arange(len(probes))).mean())


def diagnostic_accuracy(Ftr, ytr, Fte, yte):
    sc = StandardScaler().fit(Ftr)
    clf = LogisticRegression(max_iter=2000, C=1.0)
    clf.fit(sc.transform(Ftr), ytr)
    return float(clf.score(sc.transform(Fte), yte))


def run(seed=20260910, n_patients=200, n_repeats=5):
    rng = np.random.default_rng(seed)
    print("building cohort of %d synthetic patients ..." % n_patients)
    F, y = build_cohort(rng, n_patients)
    n_tr = n_patients // 2
    Ftr, ytr, Fte, yte = F[:n_tr], y[:n_tr], F[n_tr:], y[n_tr:]

    d_cell = sensitivity_cell_level()
    d_slide = sensitivity_slide_level()
    print("feature dimension p       = %d" % F.shape[1])
    print("cell-level sensitivity    = %.2f" % d_cell)
    print("slide-level sensitivity   = %.2f" % d_slide)
    print("ratio slide/cell          = %.1fx" % (d_slide / d_cell))
    print("chance re-ID accuracy     = %.4f (1/%d)" % (1.0 / n_patients, n_patients))
    print("chance diagnostic accuracy= 0.5")

    eps_grid = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0, np.inf]
    rows = []
    for eps in eps_grid:
        acc_reid_c, acc_reid_s, acc_diag_c, acc_diag_s = [], [], [], []
        for _ in range(n_repeats):
            if np.isinf(eps):
                Fc = F.copy(); Fs = F.copy()
            else:
                Fc = core.laplace_mechanism(rng, F, d_cell, eps)
                Fs = core.laplace_mechanism(rng, F, d_slide, eps)
            acc_reid_c.append(reid_accuracy(F, Fc, rng))
            acc_reid_s.append(reid_accuracy(F, Fs, rng))
            acc_diag_c.append(diagnostic_accuracy(Fc[:n_tr], ytr, Fc[n_tr:], yte))
            acc_diag_s.append(diagnostic_accuracy(Fs[:n_tr], ytr, Fs[n_tr:], yte))
        fano = core.fano_error_floor(eps if not np.isinf(eps) else 1e9, n_patients)
        rows.append({
            "eps": None if np.isinf(eps) else eps,
            "reid_cell": float(np.mean(acc_reid_c)),
            "reid_slide": float(np.mean(acc_reid_s)),
            "diag_cell": float(np.mean(acc_diag_c)),
            "diag_slide": float(np.mean(acc_diag_s)),
            "fano_max_reid_cohort": float(max(0.0, 1.0 - fano)) if not np.isinf(eps) else 1.0,
        })

    print("\n" + "=" * 92)
    print("LINKAGE VS UTILITY  (re-ID top-1 accuracy; chance = %.4f)" % (1.0 / n_patients))
    print("=" * 92)
    print("%8s | %14s %14s | %14s %14s" %
          ("eps", "reID cell-lvl", "reID slide-lvl", "diag cell-lvl", "diag slide-lvl"))
    print("-" * 92)
    for r in rows:
        e = "inf" if r["eps"] is None else ("%.2f" % r["eps"])
        print("%8s | %14.4f %14.4f | %14.4f %14.4f" %
              (e, r["reid_cell"], r["reid_slide"], r["diag_cell"], r["diag_slide"]))

    out = {
        "n_patients": n_patients,
        "feature_dim": int(F.shape[1]),
        "sensitivity_cell": d_cell,
        "sensitivity_slide": d_slide,
        "chance_reid": 1.0 / n_patients,
        "rows": rows,
    }
    with open("results_exp2.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nsaved results_exp2.json")
    return out


if __name__ == "__main__":
    run()
