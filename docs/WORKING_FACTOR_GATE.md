# Phase-1 Working-Factor Gate Report (PanNuke)

**Date:** 14 September 2026  
**Dataset:** PanNuke (Gamper et al.), HuggingFace mirror `Angelou0516/PanNuke`  
**Cache:** 1,815 stratified patches (`data/pannuke/processed_cells.npz`)  
**Attributes:** coarse cell type only (`q=5`) — Assumption 1 respected  

---

## Gate summary

| Claim | Working factor | Result | Gate |
|---|---|---|---|
| Packing / degree bound | Max degree vs `D_pack=35` at `r=15μm` | Max observed degree **32**; **0** packing violations on 400 patches | **PASS** (with caveat) |
| Sensitivity bounds | Exact node-removal vs Props 5–6 | **0 violations** on 120 graphs; attr hist tightness 1.00 | **PASS** |
| Abstraction ≠ linkage | Two-view re-ID without DP | Top-1 **23.0%** vs chance **0.25%** (**92×**) | **PASS** |
| DP operating window | Re-ID vs diagnostic accuracy over ε | Usable window **ε ∈ [5, 10]** (shifted vs synthetic [1, 2]) | **PASS** (revised) |
| Attribute restriction | Cell-type attrs only | No intensity/morphology features used | **PASS** |

**Overall:** Phase 1 gate **PASSED**. Proceed to Springer Word rewrite with honest reporting of the shifted ε window and nuclear-separation caveat.

---

## Detailed results

### Geometry (Exp A)

| Quantity | Value |
|---|---|
| Radius `r` | 15 μm |
| Assumed `r_min` (paper) | 6 μm → `D_pack = 35` |
| Empirical NN p50 | 6.97 μm |
| Empirical NN p05 | 3.57 μm |
| Empirical NN p01 | 2.37 μm |
| Max degree (raw, no truncation) | 32 |
| Mean of per-graph max degree | 6.29 |
| Packing violations vs `D_pack=35` | 0 / 400 |

**Caveat for the paper:** some nuclei are closer than 6 μm in 2D projection (p01≈2.4 μm). The packing bound with assumed `r_min=6` still held on this sample (`max deg=32≤35`), but authors should report empirical separation and retain the degree-truncation projection `Π_D` as the formal safeguard when `r_min` is violated.

### Sensitivity (Exp B)

| Query | Max exact | Bound | Violations | Tightness |
|---|---|---|---|---|
| Edge count | 19 | 35 | 0 | 0.54 |
| Degree histogram | 23 | 71 | 0 | 0.32 |
| Attribute histogram | 1 | 1 | 0 | **1.00** |
| Laplacian spectrum ℓ₂ | 6.16 | 36.5 | 0 | 0.17 |

Bounds hold. Spectral bound remains conservative (as on synthetic data).

### Linkage vs utility (Exp C)

Cohort: **n=400** real PanNuke graphs; cell-level Laplace sensitivity ≈ **52.8**; chance top-1 = **0.25%**.  
Diagnostic label: high vs low neoplastic nuclear fraction (median split).

| ε | Re-ID top-1 | Lift | Diagnostic (neo) |
|---|---|---|---|
| 0.1 | 0.31% | 1.2× | 52.6% |
| 1.0 | 0.38% | 1.5× | 52.5% |
| 2.0 | 0.63% | 2.5× | 54.3% |
| **5.0** | **2.1%** | **8.2×** | **70.0%** |
| **10.0** | **3.6%** | **14.5×** | **81.4%** |
| 50.0 | 16.7% | 67× | 95.9% |
| none | **23.0%** | **92×** | **96.5%** |

**Inferences**

1. **Novelty claim N4 is confirmed on real nuclei:** graph abstraction alone leaves strong linkage (92× chance).  
2. **DP is load-bearing** for linkage privacy on real data, same as synthetic.  
3. **Operating window shifts** to roughly **ε ∈ [5, 10]** under this feature set/sensitivity (vs synthetic ε ∈ [1, 2]). Do not claim the synthetic numbers transfer unchanged.  
4. Tissue 19-way classification from these coarse summaries is weak (~24% without noise); primary utility metric should be neoplastic burden (or a similar binary topology-aligned task).

---

## Novelty fitness for conference submission

| Lead claim | Fit after Phase 1 |
|---|---|
| Geometry-derived degree bound + projection | Supported; report empirical `r_min` |  
| Resolution-independent ceiling | Theory unchanged; still lead |
| Graph as privacy boundary for upstream images | Supported |
| Abstraction defeats reconstruction, not linkage | **Strongest empirical claim** (synthetic + PanNuke) |
| Specific ε∈[1,2] window | **Revise** to data-dependent window; cite PanNuke [5,10] |

**Framing rule:** do not claim invention of representation-based privacy (cancelable biometrics prior art). Lead with packing + ceiling + linkage/reconstruction split.

---

## Artefacts

- `data/pannuke/processed_cells.npz`  
- `sim/results_pannuke_ab.json`  
- `sim/results_pannuke_c.json`  
- `figs/fig_pannuke_privacy_utility.png`  
- `figs/fig_pannuke_geometry.png`  
- Code: `sim/pannuke_load.py`, `exp_pannuke_ab.py`, `exp_pannuke_c.py`, `make_pannuke_figures.py`

---

## Decision

**Proceed to Phase 2:** rewrite into Springer `splnproc2510` Word `.docx`, incorporating PanNuke tables/figures and the corrected ε-window statement.
