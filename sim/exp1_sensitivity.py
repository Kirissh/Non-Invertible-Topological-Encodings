"""
Experiment 1: brute-force verification of the node-sensitivity bounds.

For each sampled graph we compute the exact worst-case l1 change over every
admissible single-node removal, and compare it against the closed-form bound
claimed in Propositions 5 and 6. A bound is FALSIFIED if any realised value
exceeds it; it is TIGHT if some instance attains it.
"""

import json
import numpy as np
import networkx as nx
import core

RESULTS = {}


def exact_sensitivity(G, query, D, q, p, s=1):
    """Worst-case l1 change over all single-node removals (s = 1)."""
    base = query(G, D=D, q=q, p=p)
    worst = 0.0
    arg = None
    for v in list(G.nodes()):
        H = G.copy()
        H.remove_node(v)
        # relabel so queries that depend on node indexing stay well defined
        H = nx.convert_node_labels_to_integers(H, label_attribute=None)
        val = query(H, D=D, q=q, p=p)
        if len(val) != len(base):
            L = max(len(val), len(base))
            a = np.zeros(L); a[: len(base)] = base
            b = np.zeros(L); b[: len(val)] = val
            d = np.abs(a - b).sum()
        else:
            d = np.abs(base - val).sum()
        if d > worst:
            worst, arg = d, v
    return worst, arg


def spectrum_sensitivity_l2(G, p=None):
    """Exact l2 distance between ordered padded spectra under node removal."""
    n = G.number_of_nodes()
    base = core.laplacian_spectrum_padded(G, n)
    worst = 0.0
    for v in list(G.nodes()):
        H = G.copy()
        H.remove_node(v)
        val = core.laplacian_spectrum_padded(H, n)
        d = np.linalg.norm(base - val)
        worst = max(worst, d)
    return worst


def run_random_family(rng, n_graphs=60, n_cells=90, D=8, q=4, p=6,
                      field=220.0, r_min=6.0, r=15.0):
    rows = []
    for i in range(n_graphs):
        label = i % 2
        pts, attrs = core.make_patient(rng, label, n_cells=n_cells, field=field,
                                       r_min=r_min, q=q, n_clusters=4, spread=22.0)
        G = core.build_graph(pts, attrs, r=r, D=D)
        if G.number_of_nodes() < 10:
            continue
        Dmax = max(d for _, d in G.degree())
        rec = {"Dmax": Dmax, "n": G.number_of_nodes(), "m": G.number_of_edges()}

        for name, query, bound in [
            ("edge_count", core.q_edge_count, core.bound_edge_count),
            ("degree_hist", core.q_degree_hist, core.bound_degree_hist),
            ("triangles", core.q_triangles, core.bound_triangles),
            ("attr_hist", core.q_attr_hist, core.bound_attr_hist),
        ]:
            exact, _ = exact_sensitivity(G, query, D=D, q=q, p=p)
            rec[name] = {"exact": float(exact),
                         "bound_D": float(bound(1, D, q, p)),
                         "bound_Dmax": float(bound(1, Dmax, q, p))}

        sl2 = spectrum_sensitivity_l2(G)
        rec["spectrum_l2"] = {"exact": float(sl2),
                              "bound_D": float(core.bound_spectrum_l2(1, D)),
                              "bound_Dmax": float(core.bound_spectrum_l2(1, Dmax))}
        rows.append(rec)
    return rows


def summarise(rows):
    out = {}
    for key in ["edge_count", "degree_hist", "triangles", "attr_hist", "spectrum_l2"]:
        ex = np.array([r[key]["exact"] for r in rows])
        bD = np.array([r[key]["bound_D"] for r in rows])
        bM = np.array([r[key]["bound_Dmax"] for r in rows])
        out[key] = {
            "n_graphs": int(len(ex)),
            "violations_vs_D": int((ex > bD + 1e-9).sum()),
            "violations_vs_Dmax": int((ex > bM + 1e-9).sum()),
            "max_exact": float(ex.max()),
            "bound_at_D": float(bD[0]),
            "mean_tightness_vs_Dmax": float(np.mean(ex / np.maximum(bM, 1e-12))),
            "max_tightness_vs_Dmax": float(np.max(ex / np.maximum(bM, 1e-12))),
        }
    return out


def worked_example_grid():
    """Exact verification of the 3x3 grid example used in the paper."""
    G = nx.convert_node_labels_to_integers(nx.grid_2d_graph(3, 3))
    for i in G.nodes():
        G.nodes[i]["x"] = 0
    D = 4
    centre = [v for v, d in G.degree() if d == 4][0]
    H = G.copy(); H.remove_node(centre)
    H = nx.convert_node_labels_to_integers(H)
    for i in H.nodes():
        H.nodes[i]["x"] = 0

    hist_before = core.q_degree_hist(G, D=D)
    hist_after = core.q_degree_hist(H, D=D)
    l1_hist = float(np.abs(hist_before - hist_after).sum())

    spec_before = core.laplacian_spectrum_padded(G, 9)
    spec_after = core.laplacian_spectrum_padded(H, 9)
    l2_spec = float(np.linalg.norm(spec_before - spec_after))
    l1_spec = float(np.abs(spec_before - spec_after).sum())

    return {
        "edges_before": G.number_of_edges(),
        "edges_after": H.number_of_edges(),
        "edge_delta": G.number_of_edges() - H.number_of_edges(),
        "edge_bound_sD": 1 * D,
        "hist_before": hist_before.tolist(),
        "hist_after": hist_after.tolist(),
        "hist_l1": l1_hist,
        "hist_bound": float(core.bound_degree_hist(1, D)),
        "hist_tight": abs(l1_hist - core.bound_degree_hist(1, D)) < 1e-9,
        "spectrum_before": np.round(spec_before, 4).tolist(),
        "spectrum_after": np.round(spec_after, 4).tolist(),
        "spectrum_l2": l2_spec,
        "spectrum_l2_bound": float(core.bound_spectrum_l2(1, D)),
        "spectrum_l1": l1_spec,
        "spectrum_l1_bound": float(core.bound_spectrum_l1(1, D, p=9)),
    }


def packing_check(rng, n_trials=40):
    """Proposition 4: does max degree ever exceed the packing bound?"""
    rows = []
    for r_min, r in [(6.0, 12.0), (6.0, 15.0), (6.0, 20.0), (8.0, 20.0), (5.0, 25.0)]:
        Dpack = (1 + 2 * r / r_min) ** 2 - 1
        observed = []
        for _ in range(n_trials):
            pts = core.sample_points_min_separation(rng, 400, 300.0, r_min)
            G = core.radius_graph(pts, r)
            if G.number_of_nodes():
                observed.append(max(d for _, d in G.degree()))
        rows.append({"r_min": r_min, "r": r, "D_pack": float(Dpack),
                     "max_observed": int(max(observed)),
                     "mean_observed": float(np.mean(observed)),
                     "violated": bool(max(observed) > Dpack)})
    return rows


def knn_check(rng, n_trials=30):
    """Proposition 4 second clause: symmetrised kNN degree <= 7k."""
    rows = []
    for k in [3, 5, 8]:
        observed = []
        for _ in range(n_trials):
            pts = core.sample_points_min_separation(rng, 250, 300.0, 6.0)
            G = core.knn_graph(pts, k)
            observed.append(max(d for _, d in G.degree()))
        rows.append({"k": k, "bound_7k": 7 * k,
                     "max_observed": int(max(observed)),
                     "mean_observed": float(np.mean(observed)),
                     "violated": bool(max(observed) > 7 * k)})
    return rows


if __name__ == "__main__":
    rng = np.random.default_rng(20260910)

    print("=" * 74)
    print("EXPERIMENT 1: NODE SENSITIVITY BOUNDS")
    print("=" * 74)

    rows = run_random_family(rng)
    summary = summarise(rows)
    RESULTS["random_family"] = summary
    print("\nRandom geometric cell graphs (n~90 cells, D=8, q=4), %d graphs"
          % summary["edge_count"]["n_graphs"])
    print("%-14s %10s %10s %12s %12s" %
          ("query", "max exact", "bound(D)", "violations", "tightness"))
    print("-" * 74)
    for k, v in summary.items():
        print("%-14s %10.3f %10.3f %12d %12.3f" %
              (k, v["max_exact"], v["bound_at_D"], v["violations_vs_D"],
               v["max_tightness_vs_Dmax"]))

    print("\n" + "=" * 74)
    print("WORKED EXAMPLE: 3x3 GRID (paper Section 4.5)")
    print("=" * 74)
    we = worked_example_grid()
    RESULTS["worked_example"] = we
    print("edges before/after      : %d -> %d  (delta %d, bound sD = %d)" %
          (we["edges_before"], we["edges_after"], we["edge_delta"], we["edge_bound_sD"]))
    print("degree hist before      : %s" % we["hist_before"])
    print("degree hist after       : %s" % we["hist_after"])
    print("hist l1 / bound s(2D+1) : %.1f / %.1f   TIGHT=%s" %
          (we["hist_l1"], we["hist_bound"], we["hist_tight"]))
    print("spectrum before         : %s" % we["spectrum_before"])
    print("spectrum after          : %s" % we["spectrum_after"])
    print("spectrum l2 / bound     : %.4f / %.4f" %
          (we["spectrum_l2"], we["spectrum_l2_bound"]))
    print("spectrum l1 / bound     : %.4f / %.4f" %
          (we["spectrum_l1"], we["spectrum_l1_bound"]))

    print("\n" + "=" * 74)
    print("PROPOSITION 4: PACKING BOUND ON DEGREE")
    print("=" * 74)
    pk = packing_check(rng)
    RESULTS["packing"] = pk
    print("%8s %8s %10s %14s %12s" % ("r_min", "r", "D_pack", "max observed", "violated"))
    print("-" * 74)
    for row in pk:
        print("%8.1f %8.1f %10.1f %14d %12s" %
              (row["r_min"], row["r"], row["D_pack"], row["max_observed"], row["violated"]))

    kn = knn_check(rng)
    RESULTS["knn"] = kn
    print("\n%8s %10s %14s %12s" % ("k", "bound 7k", "max observed", "violated"))
    print("-" * 74)
    for row in kn:
        print("%8d %10d %14d %12s" %
              (row["k"], row["bound_7k"], row["max_observed"], row["violated"]))

    with open("results_exp1.json", "w") as fh:
        json.dump(RESULTS, fh, indent=2)
    print("\nsaved results_exp1.json")
