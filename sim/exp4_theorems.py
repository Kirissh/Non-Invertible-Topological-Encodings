"""
Experiment 4: numerical verification of Theorems 1 and 2, the Lemma A regimes,
and the graph-versus-pixel comparison of Proposition 3.
"""

import json
import numpy as np
import core

RES = {}

# ==========================================================================
# Theorem 2: utility loss <= kappa * Delta f / eps
# ==========================================================================


def verify_theorem2(rng, p=19, Delta=40.98, L=0.01, n_trials=20000):
    """Empirical mean utility loss against the certified bound.

    The task head u is taken L-Lipschitz w.r.t. l1; we use the worst-case linear
    head u(x) = -L * <sign vector, x>, which attains the Lipschitz constant, so
    this is the tightest possible empirical test of the bound.
    """
    rows = []
    for eps in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
        b = Delta / eps
        W = rng.laplace(0.0, b, size=(n_trials, p))
        # worst-case L-Lipschitz head: loss = L * ||W||_1
        loss = L * np.abs(W).sum(axis=1)
        bound = L * p * Delta / eps
        # high-probability form, beta = 0.05
        beta = 0.05
        hp_bound = L * p * (Delta / eps) * np.log(p / beta)
        rows.append({
            "eps": eps,
            "empirical_mean_loss": float(loss.mean()),
            "certified_mean_bound": float(bound),
            "ratio": float(loss.mean() / bound),
            "holds": bool(loss.mean() <= bound + 1e-9),
            "empirical_q95": float(np.quantile(loss, 0.95)),
            "hp_bound_95": float(hp_bound),
            "hp_holds": bool(np.quantile(loss, 0.95) <= hp_bound),
        })
    return rows


# ==========================================================================
# Theorem 1: reconstruction distortion floor
# ==========================================================================


def verify_theorem1(rng, m=4096, sigma=1.0, p=19, n_trials=4000):
    """Gaussian source, linear summary, Laplace noise, best linear adversary.

    For I ~ N(0, sigma^2 I_m) we have h(I) = (m/2) log(2 pi e sigma^2), so the
    Theorem 1 floor is gamma = sigma^2 * exp(-2 eta / m). We compare the realised
    per-coordinate MSE of the optimal linear reconstruction against gamma.
    """
    rows = []
    A = rng.normal(0, 1.0 / np.sqrt(m), size=(p, m))  # summary operator
    for eps in [0.1, 1.0, 10.0, 100.0]:
        # fit the adversary on a training split and evaluate on held-out data,
        # otherwise the least-squares fit absorbs sample noise and the measured
        # error dips below the floor for purely finite-sample reasons
        I = rng.normal(0, sigma, size=(2 * n_trials, m))
        Z = I @ A.T
        Delta = 1.0
        Zt = Z + rng.laplace(0, Delta / eps, size=Z.shape)
        Ztr, Zte = Zt[:n_trials], Zt[n_trials:]
        Itr, Ite = I[:n_trials], I[n_trials:]
        Wls, *_ = np.linalg.lstsq(Ztr, Itr, rcond=None)
        Ihat = Zte @ Wls
        mse = float(((Ite - Ihat) ** 2).mean())
        # eta in bits: the release is p noisy scalars; a generous per-release
        # capacity estimate is p * 0.5 log2(1 + SNR)
        snr = np.var(Z) / (2 * (Delta / eps) ** 2)
        eta_bits = p * 0.5 * np.log2(1 + snr)
        h_bits = (m / 2.0) * np.log2(2 * np.pi * np.e * sigma ** 2)
        gamma = core.distortion_floor(h_bits, eta_bits, m)
        rows.append({
            "eps": eps, "eta_bits": float(eta_bits),
            "empirical_mse": mse, "floor_gamma": float(gamma),
            "trivial_estimator_mse": sigma ** 2,
            "holds": bool(mse >= gamma - 1e-9),
        })
    return rows


# ==========================================================================
# Lemma A: the two regimes
# ==========================================================================


def lemma_a_regimes():
    """Contraction factor tanh(R eps / 2) in the cohort and intra-slide regimes."""
    rows = []
    for eps in [0.01, 0.1, 0.5, 1.0, 2.0]:
        for label, R in [("cohort (R=2)", 2), ("small slide (R=200)", 200),
                         ("whole slide (R=10000)", 10000)]:
            rows.append({"eps": eps, "regime": label, "R": R,
                         "tanh_factor": float(core.dobrushin_tanh(R, eps))})
    return rows


# ==========================================================================
# Proposition 3: graph route versus pixel route
# ==========================================================================


def pareto_comparison():
    """Certified utility floors and usable budget thresholds for both routes."""
    rows = []
    B = 1.0
    kappa_g = kappa_p = 1.0
    U_star, U_0 = 1.0, 0.5
    Delta_g = 40.98
    for (H, W, C) in [(64, 64, 3), (256, 256, 3), (512, 512, 3), (1024, 1024, 3)]:
        m = H * W * C
        Delta_px = m * B
        eps_g = kappa_g * Delta_g / (U_star - U_0)
        eps_p = kappa_p * Delta_px / (U_star - U_0)
        rows.append({
            "resolution": "%dx%dx%d" % (H, W, C), "m": m,
            "Delta_graph": Delta_g, "Delta_pixel": float(Delta_px),
            "sensitivity_ratio": float(Delta_px / Delta_g),
            "eps_min_graph": float(eps_g), "eps_min_pixel": float(eps_p),
            "threshold_ratio": float(eps_p / eps_g),
        })
    return rows


def structural_ceiling_table():
    rows = []
    for (H, W) in [(256, 256), (512, 512), (1024, 1024), (2048, 2048)]:
        img = core.image_entropy_bits(H, W, 3)
        ceil_ = core.structural_ceiling_bits(5000, 35, 8)
        rows.append({
            "resolution": "%dx%d" % (H, W),
            "image_bits": float(img),
            "ceiling_bits": float(ceil_),
            "ratio": float(img / ceil_),
            "log2_fiber": float(img - ceil_),
        })
    return rows


if __name__ == "__main__":
    rng = np.random.default_rng(11)

    print("=" * 86)
    print("THEOREM 2: utility loss <= kappa Delta f / eps      (worst-case Lipschitz head)")
    print("=" * 86)
    t2 = verify_theorem2(rng)
    RES["theorem2"] = t2
    print("%8s %16s %16s %10s %8s %14s %8s" %
          ("eps", "empirical mean", "certified bound", "ratio", "holds", "emp q95", "hp ok"))
    print("-" * 86)
    for r in t2:
        print("%8.2f %16.4f %16.4f %10.3f %8s %14.4f %8s" %
              (r["eps"], r["empirical_mean_loss"], r["certified_mean_bound"],
               r["ratio"], r["holds"], r["empirical_q95"], r["hp_holds"]))

    print("\n" + "=" * 86)
    print("THEOREM 1: reconstruction MSE >= gamma(eps)")
    print("=" * 86)
    t1 = verify_theorem1(rng)
    RES["theorem1"] = t1
    print("%8s %12s %16s %16s %16s %8s" %
          ("eps", "eta (bits)", "empirical MSE", "floor gamma", "trivial est.", "holds"))
    print("-" * 86)
    for r in t1:
        print("%8.2f %12.2f %16.5f %16.5f %16.5f %8s" %
              (r["eps"], r["eta_bits"], r["empirical_mse"], r["floor_gamma"],
               r["trivial_estimator_mse"], r["holds"]))

    print("\n" + "=" * 86)
    print("LEMMA A: contraction factor tanh(R eps / 2) by regime")
    print("=" * 86)
    la = lemma_a_regimes()
    RES["lemma_a"] = la
    print("%8s %26s %16s" % ("eps", "regime", "tanh factor"))
    print("-" * 86)
    for r in la:
        print("%8.2f %26s %16.6f" % (r["eps"], r["regime"], r["tanh_factor"]))

    print("\n" + "=" * 86)
    print("PROPOSITION 3: graph versus pixel route")
    print("=" * 86)
    pc = pareto_comparison()
    RES["pareto"] = pc
    print("%14s %12s %16s %18s %16s" %
          ("resolution", "m", "Delta pixel", "sens. ratio", "eps threshold x"))
    print("-" * 86)
    for r in pc:
        print("%14s %12d %16.0f %18.1f %16.1f" %
              (r["resolution"], r["m"], r["Delta_pixel"],
               r["sensitivity_ratio"], r["threshold_ratio"]))

    print("\n" + "=" * 86)
    print("PROPOSITION 1: structural ceiling is resolution independent")
    print("=" * 86)
    sc = structural_ceiling_table()
    RES["ceiling"] = sc
    print("%14s %18s %18s %12s %18s" %
          ("resolution", "image bits", "ceiling bits", "ratio", "log2 fiber size"))
    print("-" * 86)
    for r in sc:
        print("%14s %18.3e %18.3e %12.1f %18.3e" %
              (r["resolution"], r["image_bits"], r["ceiling_bits"],
               r["ratio"], r["log2_fiber"]))

    with open("results_exp4.json", "w") as fh:
        json.dump(RES, fh, indent=2)
    print("\nsaved results_exp4.json")
