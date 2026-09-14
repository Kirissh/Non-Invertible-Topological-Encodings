"""
Experiment 3: two-view re-identification, the methodologically correct version.

In Experiment 2 the probe vector was a noisy copy of the very vector held in the
gallery, so at zero noise matching is trivially perfect and tells us nothing. Here
the adversary's gallery is built from an INDEPENDENT ACQUISITION of the same
tissue: the same underlying cell layout re-imaged with registration jitter, a
different segmentation yield, and independent attribute quantisation noise.

This measures what actually matters: how much STABLE biometric identity survives
the topological transform. If two separate scans of the same patient still map to
matchable graph summaries, the representation is biometric regardless of how large
its preimage is.
"""

import json
import numpy as np
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


def features(G):
    return np.concatenate([
        core.q_degree_hist(G, D=D),
        core.q_attr_hist(G, q=Q),
        core.q_spectrum(G, p=P_SPEC, n_pad=max(G.number_of_nodes(), P_SPEC)),
    ])


def acquire(rng, pts, attrs, jitter=1.5, keep=0.88, attr_flip=0.05):
    """Simulate one imaging + segmentation pass over a fixed underlying tissue."""
    keep_mask = rng.random(len(pts)) < keep
    p = pts[keep_mask] + rng.normal(0, jitter, size=(keep_mask.sum(), 2))
    a = attrs[keep_mask].copy()
    flip = rng.random(len(a)) < attr_flip
    a[flip] = rng.integers(0, Q, size=int(flip.sum()))
    G = core.build_graph(p, a, r=R_RADIUS, D=D)
    return features(G)


def build_two_view_cohort(rng, n_patients):
    """Each patient contributes two independent acquisitions of the same tissue."""
    A, B, y = [], [], []
    for i in range(n_patients):
        label = i % 2
        pts, attrs = core.make_patient(rng, label, n_cells=N_CELLS, field=FIELD,
                                       r_min=R_MIN, q=Q, n_clusters=6, spread=30.0)
        A.append(acquire(rng, pts, attrs))
        B.append(acquire(rng, pts, attrs))
        y.append(label)
    return np.array(A), np.array(B), np.array(y)


def reid_topk(gallery, probes, k=1):
    mu, sd = gallery.mean(0), gallery.std(0) + 1e-9
    Gz = (gallery - mu) / sd
    Pz = (probes - mu) / sd
    d = np.linalg.norm(Pz[:, None, :] - Gz[None, :, :], axis=-1)
    order = np.argsort(d, axis=1)[:, :k]
    truth = np.arange(len(probes))[:, None]
    return float((order == truth).any(axis=1).mean())


def diagnostic_accuracy(Ftr, ytr, Fte, yte):
    sc = StandardScaler().fit(Ftr)
    clf = LogisticRegression(max_iter=3000)
    clf.fit(sc.transform(Ftr), ytr)
    return float(clf.score(sc.transform(Fte), yte))


def sensitivity_cell(s=1):
    return (core.bound_degree_hist(s, D) + core.bound_attr_hist(s)
            + core.bound_spectrum_l1(s, D, p=P_SPEC))


def run(seed=7, n_patients=200, n_repeats=5):
    rng = np.random.default_rng(seed)
    print("building two-view cohort of %d patients ..." % n_patients)
    A, B, y = build_two_view_cohort(rng, n_patients)
    d_cell = sensitivity_cell()
    chance = 1.0 / n_patients
    n_tr = n_patients // 2

    print("feature dim = %d, cell-level sensitivity = %.2f" % (A.shape[1], d_cell))
    print("chance re-ID = %.4f,  chance top-5 = %.4f" % (chance, 5.0 / n_patients))

    eps_grid = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0, None]
    rows = []
    for eps in eps_grid:
        r1, r5, dg = [], [], []
        for _ in range(n_repeats):
            Bn = B.copy() if eps is None else core.laplace_mechanism(rng, B, d_cell, eps)
            r1.append(reid_topk(A, Bn, k=1))
            r5.append(reid_topk(A, Bn, k=5))
            dg.append(diagnostic_accuracy(Bn[:n_tr], y[:n_tr], Bn[n_tr:], y[n_tr:]))
        rows.append({"eps": eps,
                     "reid_top1": float(np.mean(r1)),
                     "reid_top5": float(np.mean(r5)),
                     "diag": float(np.mean(dg)),
                     "reid_lift": float(np.mean(r1) / chance)})

    print("\n" + "=" * 84)
    print("TWO-VIEW RE-IDENTIFICATION  (gallery = scan A, probe = noisy scan B)")
    print("=" * 84)
    print("%8s | %10s %10s %12s | %10s" %
          ("eps", "top-1", "top-5", "lift x chance", "diagnostic"))
    print("-" * 84)
    for r in rows:
        e = "none" if r["eps"] is None else ("%.2f" % r["eps"])
        print("%8s | %10.4f %10.4f %12.1f | %10.4f" %
              (e, r["reid_top1"], r["reid_top5"], r["reid_lift"], r["diag"]))

    out = {"n_patients": n_patients, "chance_top1": chance,
           "sensitivity_cell": d_cell, "feature_dim": int(A.shape[1]), "rows": rows}
    with open("results_exp3.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nsaved results_exp3.json")
    return out


if __name__ == "__main__":
    run()
