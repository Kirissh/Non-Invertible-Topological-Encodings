# Results Briefing — Privacy as a Property of Representation

**To:** Supervisors / Project Committee  
**From:** [Your Name]  
**Date:** 10 September 2026  
**Re:** Simulation results and what they imply for the project  

---

## Purpose of this note

We ran a numerical study of the proposed pipeline (image → cell graph → node-level differential privacy → release). This note summarises what the results show, what they do *not* show, and how we propose to proceed.

---

## Main finding in one sentence

**Turning a medical image into a cell graph preserves diagnostic signal but does not, by itself, prevent patient re-identification; a differentially private mechanism is required for linkage privacy, and there is a usable operating window around ε ∈ [1, 2].**

---

## What we tested

Synthetic tissue layouts (diffuse vs clustered / tumour-like) were converted to radius cell graphs. We measured:

1. Whether the theoretical sensitivity and utility bounds hold numerically  
2. Whether an adversary can match a released graph summary to an enrolled patient (re-identification)  
3. Whether a simple diagnostic classifier still works after privacy noise  

Re-identification used a **two-view** protocol: gallery from scan A, probe from an independent scan B of the same tissue (jitter, incomplete segmentation, attribute noise). Chance top-1 accuracy with 200 patients is **0.5%**.

---

## Key numbers

### A. Graph alone is not enough for identity privacy

| Condition | Re-ID top-1 | Re-ID top-5 | Diagnostic accuracy |
|---|---|---|---|
| No privacy mechanism | **21.0%** (42× chance) | **52.5%** | **100%** |

**Inference:** Abstraction destroys enough information to block image reconstruction, but retains stable structure that still links patients. “Graphs are inherently private” is too strong for the linkage threat.

### B. There is a practical privacy–utility window

| Privacy budget ε | Re-ID top-1 | Lift over chance | Diagnostic accuracy | Interpretation |
|---|---|---|---|---|
| 0.1 | 0.5% | 1.0× | 50.6% | Too private; diagnosis collapses |
| **1.0** | **1.0%** | **2.0×** | **80.6%** | Strong candidate operating point |
| **2.0** | **1.6%** | **3.2×** | **94.2%** | Best measured trade-off |
| 5.0 | 6.0% | 12× | 99.8% | Diagnosis excellent; privacy weakening |
| none | 21.0% | 42× | 100% | No privacy |

**Inference:** For this setup, **ε ≈ 1–2** keeps diagnosis high while driving re-identification close to chance.

### C. The supporting maths checks out

- Sensitivity bounds: **0 violations** across 60 random graphs; 3 of 5 bounds attained exactly  
- Utility bound (Theorem 2): empirical loss matches the certified bound (ratio ≈ 1.0)  
- Reconstruction floor (Theorem 1): held under a held-out adversary test  
- Structural ceiling is resolution-independent: image entropy grows with resolution; the graph information ceiling does not  

---

## Corrected project thesis

| Threat | What stops it | Status |
|---|---|---|
| Reconstructing the original image | Topological abstraction (many-to-one collapse) | Supported by theory + simulation |
| Linking a release to a named patient | Node-level DP noise | Supported empirically in the ε ∈ [1, 2] window |
| Claiming graphs alone are enough | — | **Refuted** for linkage; this is now an explicit contribution |

**Working thesis:** abstraction governs reconstruction; perturbation governs linkage; both are required.

---

## Caveats (please note)

1. Results are on **synthetic** tissue, not real whole-slide images.  
2. Near-chance re-ID at ε ∈ [1, 2] is an **empirical** observation, not a full formal certificate of patient-level protection.  
3. Calibrating noise to whole-slide / patient-level neighbouring currently destroys utility in this mechanism family (≈31× larger sensitivity). Closing that gap is the main open problem.  
4. The attack used is nearest-neighbour matching; stronger attacks should be tested later.

---

## Proposed next steps

1. Keep the theoretical claims, but lead with the **reconstruction vs linkage** distinction.  
2. Treat the ε ∈ [1, 2] window as a working hypothesis to validate on real pathology graphs.  
3. Prioritise mechanism design for **patient-level** privacy without collapsing utility.  
4. Decide venue framing (MICCAI / IPMI / PETS) once we confirm whether real-data validation is required for the first submission.

---

## Attachments / artefacts

- Springer LNCS draft: `springer_main.pdf`  
- Full novelty and findings write-up: `FINDINGS_AND_NOVELTY.md`  
- Key figure: `figs/fig_privacy_utility.png`  
- Reproducible code: `sim/` (`exp1`–`exp4`, `make_figures.py`)

Happy to walk through the figure and the ε table in our next meeting.
