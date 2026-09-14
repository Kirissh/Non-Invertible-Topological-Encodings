# Property-Representation

Public code and experimental artefacts for **representation-based privacy** of medical images via cell graphs and node-level differential privacy.

> Manuscript drafts (LaTeX / Word / PDF) are **not** included in this repository.

## Idea in one line

Convert pathology images to **cell graphs** (diagnosis-friendly), then apply **node-level DP** (identity-hardening). Abstraction helps against reconstruction; DP is what reduces linkage.

## What’s here

| Path | Contents |
|---|---|
| `sim/` | Experiment code (synthetic + PanNuke) |
| `results/` | Saved JSON metrics |
| `figs/` | Privacy–utility and geometry plots |
| `docs/` | Briefings, novelty notes, meeting write-up |

## Key public result (PanNuke)

Without DP, two-view re-identification is ~**23%** top-1 (~**92×** chance) while neoplastic diagnosis stays high. With Laplace noise, a usable window appears near **ε ∈ [5, 10]**. See `figs/fig_pannuke_privacy_utility.png` and `docs/WORKING_FACTOR_GATE.md`.

## Setup

```bash
python -m pip install numpy scipy networkx matplotlib scikit-learn datasets
```

PanNuke is loaded via Hugging Face (`Angelou0516/PanNuke`) on first run. Cite [Gamper et al., ECDP 2019](https://doi.org/10.1007/978-3-030-23937-4_2).

## Reproduce

```bash
cd sim

# Synthetic checks
python exp1_sensitivity.py
python exp3_reid_twoview.py
python exp4_theorems.py
python make_figures.py

# Real PanNuke working factors
python build_pannuke_cache.py   # writes ../data/pannuke/processed_cells.npz (gitignored)
python exp_pannuke_ab.py
python exp_pannuke_c.py
python make_pannuke_figures.py
```

JSON outputs are written under `sim/` by the scripts; copies of the last run live in `results/`.

## Docs to read first

1. `docs/WORKING_FACTOR_GATE.md` — pass/fail on real data  
2. `docs/RESULTS_BRIEFING.md` — short results summary  
3. `docs/MEETING_WRITEUP.md` — plain-English explanation  

## License / data

- Code in this repo: use freely for research unless otherwise noted.  
- PanNuke is third-party data (typically CC BY-NC-SA); download it yourself — we do **not** redistribute raw images or masks here.

## Citation

If you use this code, please also cite PanNuke and the related graph / DP literature listed in `docs/FINDINGS_AND_NOVELTY.md`.
