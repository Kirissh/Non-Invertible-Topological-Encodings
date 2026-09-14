"""
Core utilities for the simulation study.

Implements the abstraction pipeline  I -> G -> Gtilde -> Ztilde  described in the
paper, together with the graph queries, sensitivity formulas and DP mechanisms
whose bounds we test numerically.

Conventions
-----------
* Distances are in micrometres.
* Information is reported in bits unless a function name says nats.
* All randomness flows through an explicit numpy Generator for reproducibility.
"""

import numpy as np
import networkx as nx

# --------------------------------------------------------------------------
# Tissue synthesis:  the "image" I, represented by its ground-truth cell layout
# --------------------------------------------------------------------------


def sample_points_min_separation(rng, n_target, field, r_min, max_tries=40):
    """Dart-throwing sample of points in [0, field]^2 with pairwise distance >= r_min.

    This enforces the physical separation condition that Proposition 4 (packing)
    relies on: nuclei are physical objects and cannot overlap.
    """
    pts = []
    tries = 0
    while len(pts) < n_target and tries < n_target * max_tries:
        cand = rng.uniform(0, field, size=2)
        if not pts:
            pts.append(cand)
            continue
        d = np.linalg.norm(np.asarray(pts) - cand, axis=1)
        if d.min() >= r_min:
            pts.append(cand)
        tries += 1
    return np.asarray(pts)


def sample_clustered_points(rng, n_target, field, r_min, n_clusters, spread,
                            max_tries=60):
    """Matern-style cluster process with a hard minimum separation.

    Used as the 'tumour' class: cells aggregate into clusters, which is the
    topological signature pathologists read as diagnostic.
    """
    centres = rng.uniform(0, field, size=(n_clusters, 2))
    pts = []
    tries = 0
    while len(pts) < n_target and tries < n_target * max_tries:
        c = centres[rng.integers(n_clusters)]
        cand = c + rng.normal(0, spread, size=2)
        tries += 1
        if np.any(cand < 0) or np.any(cand > field):
            continue
        if pts:
            d = np.linalg.norm(np.asarray(pts) - cand, axis=1)
            if d.min() < r_min:
                continue
        pts.append(cand)
    return np.asarray(pts)


def make_patient(rng, label, n_cells=300, field=400.0, r_min=6.0, q=4,
                 n_clusters=6, spread=28.0):
    """Generate one synthetic patient.

    label 0 = diffuse / healthy-like layout
    label 1 = clustered / tumour-like layout

    Returns the centroids and the categorical node attributes, which together
    play the role of the segmenter output sigma(I).
    """
    if label == 0:
        pts = sample_points_min_separation(rng, n_cells, field, r_min)
    else:
        pts = sample_clustered_points(rng, n_cells, field, r_min,
                                      n_clusters, spread)
    attrs = rng.integers(0, q, size=len(pts))
    return pts, attrs


# --------------------------------------------------------------------------
# Topology builder tau:  centroids -> graph
# --------------------------------------------------------------------------


def radius_graph(points, r):
    """Radius graph: edge iff centroid distance <= r."""
    n = len(points)
    G = nx.Graph()
    G.add_nodes_from(range(n))
    if n == 0:
        return G
    d = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=-1)
    iu = np.triu_indices(n, k=1)
    mask = d[iu] <= r
    edges = [(int(a), int(b)) for a, b, m in zip(iu[0], iu[1], mask) if m]
    G.add_edges_from(edges)
    return G


def knn_graph(points, k):
    """Symmetrised k-nearest-neighbour graph."""
    n = len(points)
    G = nx.Graph()
    G.add_nodes_from(range(n))
    if n <= 1:
        return G
    d = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=-1)
    np.fill_diagonal(d, np.inf)
    kk = min(k, n - 1)
    nbrs = np.argsort(d, axis=1)[:, :kk]
    for i in range(n):
        for j in nbrs[i]:
            G.add_edge(int(i), int(j))
    return G


def truncate_degree(G, D, rng=None):
    """Projection Pi_D: greedily delete edges until every degree is <= D.

    Identity on graphs that already satisfy the bound, which is the property the
    paper relies on when it argues no utility is lost in the normal case.
    """
    H = G.copy()
    while True:
        over = [v for v, dg in H.degree() if dg > D]
        if not over:
            break
        v = max(over, key=lambda u: H.degree(u))
        nbrs = list(H.neighbors(v))
        nbrs.sort(key=lambda u: H.degree(u), reverse=True)
        H.remove_edge(v, nbrs[0])
    return H


def build_graph(points, attrs, r, D, construction="radius", k=5):
    """Full transform Phi = tau o sigma, followed by degree truncation."""
    if construction == "radius":
        G = radius_graph(points, r)
    elif construction == "knn":
        G = knn_graph(points, k)
    else:
        raise ValueError(construction)
    G = truncate_degree(G, D)
    for i in G.nodes():
        G.nodes[i]["x"] = int(attrs[i])
    return G


# --------------------------------------------------------------------------
# Graph queries f  (the topological summaries the diagnostic head consumes)
# --------------------------------------------------------------------------


def q_edge_count(G, D=None, q=None, p=None):
    return np.array([G.number_of_edges()], dtype=float)


def q_degree_hist(G, D, q=None, p=None):
    h = np.zeros(D + 1)
    for _, dg in G.degree():
        h[min(dg, D)] += 1
    return h


def q_triangles(G, D=None, q=None, p=None):
    return np.array([sum(nx.triangles(G).values()) / 3.0], dtype=float)


def q_attr_hist(G, D=None, q=4, p=None):
    h = np.zeros(q)
    for i in G.nodes():
        h[G.nodes[i]["x"]] += 1
    return h


def q_clustering_mean(G, D=None, q=None, p=None):
    c = nx.clustering(G)
    if not c:
        return np.array([0.0])
    return np.array([float(np.mean(list(c.values())))])


def laplacian_spectrum_padded(G, n_pad):
    """Ordered (decreasing) combinatorial Laplacian spectrum, zero-padded to n_pad.

    Padding to a fixed public size is what makes spectra of graphs with different
    node counts comparable, and is exactly the construction used in Proposition 6.
    """
    n = G.number_of_nodes()
    if n == 0:
        return np.zeros(n_pad)
    L = nx.laplacian_matrix(G, nodelist=sorted(G.nodes())).toarray().astype(float)
    ev = np.linalg.eigvalsh(L)
    ev = np.sort(ev)[::-1]
    out = np.zeros(n_pad)
    out[: min(n, n_pad)] = ev[: min(n, n_pad)]
    return out


def q_spectrum(G, D=None, q=None, p=8, n_pad=None):
    n_pad = n_pad if n_pad is not None else max(G.number_of_nodes(), p)
    return laplacian_spectrum_padded(G, n_pad)[:p]


# --------------------------------------------------------------------------
# Theoretical sensitivity bounds from the paper
# --------------------------------------------------------------------------


def bound_edge_count(s, D, q=None, p=None):
    return s * D


def bound_degree_hist(s, D, q=None, p=None):
    return s * (2 * D + 1)


def bound_triangles(s, D, q=None, p=None):
    return s * D * (D - 1) / 2.0


def bound_attr_hist(s, D=None, q=None, p=None):
    return float(s)


def bound_clustering_mean(s, D, q=None, p=None):
    # profile bound s(D+1) divided by n when the released statistic is the mean;
    # reported here in the profile form used by Proposition 5.
    return s * (D + 1)


def bound_spectrum_l2(s, D, q=None, p=None):
    return s * np.sqrt(D ** 2 + 3.0 * D)


def bound_spectrum_l1(s, D, q=None, p=8):
    return s * np.sqrt(p) * np.sqrt(D ** 2 + 3.0 * D)


# --------------------------------------------------------------------------
# Structural ceiling  C(n, D, q)   (Proposition 1)
# --------------------------------------------------------------------------


def structural_ceiling_bits(n, D, q):
    """C(n,D,q) = (nD/2) log(en/D) + n log q, converted to bits.

    Contains no dependence on H, W or C. That is the paradigm claim.
    """
    nats = (n * D / 2.0) * np.log(np.e * n / D) + n * np.log(q)
    return nats / np.log(2.0)


def image_entropy_bits(H, W, C, bits_per_channel=8):
    return H * W * C * bits_per_channel


# --------------------------------------------------------------------------
# Differential privacy mechanisms
# --------------------------------------------------------------------------


def laplace_mechanism(rng, value, sensitivity, eps):
    """Add Laplace(sensitivity/eps) noise coordinatewise."""
    b = sensitivity / eps
    return value + rng.laplace(0.0, b, size=np.shape(value))


def dobrushin_tanh(R, eps):
    """Contraction coefficient bound eta_TV <= tanh(R eps / 2) from Lemma A."""
    return np.tanh(R * eps / 2.0)


def lemma_a_eta_bits(R, eps, n, D, q):
    """The leakage bound eta(eps) of Lemma A, in bits."""
    return dobrushin_tanh(R, eps) * structural_ceiling_bits(n, D, q)


def fano_error_floor(eta_nats, N):
    """Fano lower bound on re-identification error probability (Corollary 3)."""
    return 1.0 - (eta_nats + np.log(2.0)) / np.log(N)


def distortion_floor(h_bits, eta_bits, m):
    """Theorem 1 floor gamma(eps), for a source with differential entropy h.

    Both h and eta are supplied in bits; the result is a per-coordinate squared
    error in the units of the source.
    """
    h_nats = h_bits * np.log(2.0)
    eta_nats = eta_bits * np.log(2.0)
    return np.exp(2.0 * (h_nats - eta_nats) / m) / (2.0 * np.pi * np.e)
