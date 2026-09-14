# Novelty, Findings, and Publication Case

Written after building and running the simulation suite, then Phase-1 PanNuke validation.
See also `WORKING_FACTOR_GATE.md` for the pass/fail publication gate.

---

## 0. Phase-1 Gate (PanNuke) — PASSED

Real nuclei confirm the core novelty claim and revise the ε window:

| Gate | Result |
|---|---|
| Packing vs D_pack=35 | max degree 32; 0 violations |
| Sensitivity bounds | 0 violations |
| Abstraction ≠ linkage | 23% top-1 re-ID = **92× chance** without DP |
| DP window | usable near **ε∈[5,10]** (not synthetic [1,2]) |
| Coarse attributes only | q=5 cell types |

Deliverable for submission formatting: `Privacy_Representation_Springer.docx`.

---

## 1. What Is Actually Novel

I have graded each claim honestly. Overselling a weak novelty claim is the fastest way to get desk-rejected, so it matters that you know which of these to lead with and which to soft-pedal.

| # | Claim | Novelty | Verdict |
|---|---|---|---|
| N1 | Node degree bound derived from **physical tissue geometry** (packing on minimum nuclear separation) rather than assumed | **Strong** | Lead with this |
| N2 | **Resolution-independent structural ceiling** on what a graph release can leak about its source image | **Strong** | Lead with this |
| N3 | Node-DP applied to graphs that are **outputs of a lossy transform of a more sensitive object**, rather than to graphs that are the data | **Strong** | The literature gap |
| N4 | Empirical demonstration that **abstraction defeats reconstruction but not linkage** | **Strong** | Your most defensible contribution |
| N5 | Composite pipeline with post-processing closure over arbitrary embeddings | Medium | Supporting |
| N6 | Resolution-driven separation from pixel-space DP, ratio $\Theta(m)$ | Weak to medium | Do not lead with this |
| N7 | The "access-based vs representation-based" framing | **Weak** | Has prior art |

### Why N1 is your strongest technical novelty

Node-level differential privacy on graphs is known to be brutally hard: in an unrestricted graph family a single node can touch every other node, so a degree histogram has sensitivity $\Theta(n)$ and a triangle count $\Theta(n^2)$. The universal escape hatch in that literature is to *assume* a maximum degree bound $D$. Reviewers dislike this because the assumption is doing all the work and nothing justifies it.

You do not assume it. You derive it:

$$\deg(v) \le \left(1 + \frac{2r}{r_{\min}}\right)^2 - 1$$

from the fact that nuclei are physical objects that cannot overlap. $r_{\min}$ is a measurable property of the tissue preparation and $r$ is the analyst's choice. At $r = 15\,\mu m$ and $r_{\min} = 6\,\mu m$ this gives $D \le 35$ against the $n \approx 5000$ that an unrestricted analysis would force, a 140-fold reduction in required noise.

I have not seen this move made anywhere. It converts the standard weak point of node-DP into a strength, and it only works in this application domain, which is exactly what a domain-specific privacy paper should look like.

### Why N2 is genuinely surprising

The ceiling is

$$\mathcal{C}(n,D,q) = \frac{nD}{2}\log\frac{en}{D} + n\log q$$

There is no $H$, no $W$, no $C$ in it. Buy a scanner with twice the linear resolution, and the image entropy quadruples while the ceiling does not move at all. **Improving your imaging hardware strictly improves your privacy.** That is a counterintuitive, quotable result and the graph-DP literature has no analogue because those papers have no upstream image.

Verified numerically (`sim/exp4_theorems.py`):

| Resolution | Image entropy | Ceiling | Ratio |
|---|---|---|---|
| $256^2$ | $1.57\times10^6$ bits | $7.68\times10^5$ | $2.0\times$ |
| $512^2$ | $6.29\times10^6$ | $7.68\times10^5$ | $8.2\times$ |
| $1024^2$ | $2.52\times10^7$ | $7.68\times10^5$ | $32.8\times$ |
| $2048^2$ | $1.01\times10^8$ | $7.68\times10^5$ | $131.1\times$ |

Honest caveat: at $256^2$ the ratio is only 2, so the argument is weak at low resolution. It becomes compelling only at whole-slide scale. That is fine, because whole-slide scale is the actual use case, but state it rather than let a reviewer find it.

### Why N7 is weak and should not be your headline

The idea that a non-invertible transform can provide privacy is not new. **Cancelable biometrics** (Ratha et al., 2001 onward) is an entire subfield built on exactly this principle: apply a non-invertible transform to a fingerprint or iris template so that a stolen template cannot be reversed. If you frame the paper as "we introduce representation-based privacy," a reviewer who knows that literature will push back hard.

Frame it instead as: *representation-based privacy has been studied for biometric templates, but never for medical images, never with a transform the diagnostic community independently adopted, and never with a quantified information-theoretic gap between diagnostic and biometric sufficiency.* That is defensible.

---

## 2. What We Are Finding

The simulation produced one result that changes the paper, and several that confirm it.

### Finding 1 (the important one): abstraction defeats reconstruction but NOT linkage

This is the headline and it is a **negative result about your own framework**, which is exactly why it makes the paper credible.

**Setup.** 200 synthetic patients. The adversary holds a gallery of clean topological summaries from one imaging pass. It observes a released summary from an *independent second acquisition* of the same tissue, with registration jitter, 88% segmentation yield, and independent attribute noise. It matches by nearest neighbour. Chance is 0.5%.

**Result with no privacy mechanism: 21.0% top-1, 52.5% top-5. That is 42 times chance.**

The topological representation carries substantial *stable* biometric identity that survives re-imaging and re-segmentation. The many-to-one collapse does not prevent this.

**Why this does not contradict your theory.** It does not. Proposition 1 and Theorem 1 are about *reconstruction* and they remain correct. The issue is arithmetic:

- Identifying one patient among $10^4$ requires about **14 bits**.
- The structural ceiling is about **$7.7\times10^5$ bits**.

A ceiling five orders of magnitude above the linkage requirement is simply not binding for linkage. You can destroy essentially everything needed to redraw the image while retaining vastly more than enough to name its owner.

**What this means for the paper.** The mechanism $M$ is not a refinement of the argument. It is the component that carries the linkage guarantee. The corrected thesis, which is what the Springer draft now states, is:

> **Abstraction governs reconstruction. Perturbation governs linkage. Both are required.**

This is a better paper than "graphs are inherently private," because it is true and because it gives you a two-part story where each part has a proof and an experiment.

### Finding 2: there is a real, quantified operating window

From `sim/exp3_reid_twoview.py`:

| $\varepsilon$ | Re-ID top-1 | Lift over chance | Diagnostic accuracy |
|---|---|---|---|
| 0.1 | 0.50% | 1.0× | 50.6% (chance) |
| 0.5 | 1.10% | 2.2× | 55.8% |
| **1.0** | **1.00%** | **2.0×** | **80.6%** |
| **2.0** | **1.60%** | **3.2×** | **94.2%** |
| 5.0 | 6.00% | 12.0× | 99.8% |
| 10.0 | 9.70% | 19.4× | 100% |
| 50.0 | 22.4% | 44.8× | 100% |
| none | 21.0% | 42.0× | 100% |

At $\varepsilon \in [1,2]$ linkage sits at 2 to 3 times chance while diagnosis runs at 81% to 94%. Below 0.5 both collapse; above 5 privacy collapses. That window is the practical contribution and it is the kind of concrete number reviewers want.

### Finding 3: the sensitivity bounds are correct and three of five are exactly tight

Brute-force enumeration over every single-node removal across 60 random cell graphs (`sim/exp1_sensitivity.py`). **Zero violations.**

| Query | Bound | Max realised | Tightness |
|---|---|---|---|
| Edge count | $sD$ | 8.00 | **1.00 (attained)** |
| Degree histogram | $s(2D+1)$ | 17.00 | **1.00 (attained)** |
| Attribute histogram | $s$ | 1.00 | **1.00 (attained)** |
| Triangle count | $s\binom{D}{2}$ | 15.00 | 0.83 |
| Laplacian spectrum | $s\sqrt{D^2+3D}$ | 2.96 | 0.50 |

Three bounds are attained exactly, meaning they cannot be improved without further assumptions. The spectral bound is loose by about 2×, which is expected since Hoffman-Wielandt is worst-case over eigenvector alignments. That is a legitimate open problem to list.

The $3\times3$ grid worked example reproduces exactly: 4 edges destroyed against bound 4; degree histogram $\ell_1$ distance 9.0 against bound 9.0; spectral $\ell_2$ distance 3.140 against bound 5.29.

### Finding 4: the packing bound is valid but conservative

Never violated across every configuration tested. But at $r=15$, $r_{\min}=6$ the bound is 35 while the largest degree actually observed was **8**. Realistic tissue does not come close to the worst-case packing. Useful to know when calibrating noise, and worth reporting rather than hiding.

### Finding 5: Lemma A degenerates exactly where the paper admitted it would

The contraction factor $\tanh(R\varepsilon/2)$:

| $\varepsilon$ | Cohort, $R=2$ | Region, $R=200$ | Slide, $R=10^4$ |
|---|---|---|---|
| 0.01 | 0.0100 | 0.762 | 1.000 |
| 0.1 | 0.0997 | 1.000 | 1.000 |
| 1.0 | 0.762 | 1.000 | 1.000 |

In the cohort regime you get a genuine hundred-fold contraction. In the intra-slide regime the factor is 1.000 and the lemma contributes **nothing** beyond the structural ceiling. This confirms numerically what the paper stated in prose. The strong result is the per-patient corollary, not the lemma.

### Finding 6: Theorems 1 and 2 verify

- **Theorem 2** (utility): using the worst-case Lipschitz head, the ratio of empirical loss to certified bound was $1.000 \pm 0.002$ over 20,000 trials. The bound is **attained with equality in expectation**, so it is tight, not conservative. The high-probability form held at the 95th percentile in every case.
- **Theorem 1** (reconstruction): Gaussian source in $\mathbb{R}^{4096}$, optimal linear adversary fitted on a training split and evaluated held-out. Realised MSE exceeded the floor $\gamma(\varepsilon)$ at every budget and matched the trivial estimator's error to within 0.5%, confirming the adversary is reduced to guessing the population mean.

### Finding 7: the pixel separation scales as predicted

| Resolution | $m$ | Threshold ratio |
|---|---|---|
| $64^2\times3$ | 12,288 | 300× |
| $256^2\times3$ | 196,608 | 4,798× |
| $512^2\times3$ | 786,432 | 19,191× |
| $1024^2\times3$ | 3,145,728 | 76,763× |

Exactly linear in $m$, as Proposition 3 predicts.

---

## 3. Is It Theoretically Possible?

**Yes, with one important correction and one unsolved problem.**

### What is sound

| Result | Status | Note |
|---|---|---|
| Prop 1, structural ceiling | **Sound** | Elementary counting, verified |
| Prop 2, post-processing and composition | **Sound** | Standard DP, trivially correct |
| Lemma A, leakage bound | **Sound but weak** | Vacuous in the intra-slide regime, confirmed numerically |
| Cor 1, per-patient bound | **Sound and strong** | Follows from Cuff and Yu; no dependence on $n$ or resolution |
| Thm 1, reconstruction floor | **Sound** | Standard rate-distortion, verified |
| Thm 2, utility bound | **Sound and tight** | Verified to within 0.2% |
| Prop 3, separation | **Sound as stated** | It is a floor comparison, not an impossibility result |
| Prop 4, packing | **Sound** | Never violated; conservative |
| Props 5 and 6, sensitivities | **Sound** | Zero violations; three attained exactly |

### The correction you must make

The original draft conflated two threats. Corollary 3 (Fano) as originally written plugs in $\eta(\varepsilon)$ from Lemma A, but in the intra-slide regime that quantity is around $10^5$ nats while $\log N \approx 9$, so the bound returns a large negative number and is **vacuous**. The corollary is only meaningful with the per-patient $\eta$ from Corollary 1, which requires the cohort regime.

The Springer draft now states this explicitly. Leaving it uncorrected would have been the single most likely cause of rejection, because it is precisely the kind of thing a careful theory reviewer checks.

### The unsolved problem

Node-level privacy with $s=1$ formally protects **the presence of one cell**. It does not protect **the participation of a patient**, whose identity is spread across all $n$ nodes. To certify patient-level protection you need the neighbouring unit to be the whole slide.

I tested that. Slide-level sensitivity is **31.6× larger**, and at every budget below $\varepsilon = 50$ it drove diagnostic accuracy to chance. So:

> Certified patient-level protection is not currently achievable with useful accuracy under the Laplace mechanism family.

The near-chance linkage observed at $\varepsilon \in [1,2]$ is therefore an **empirical** property, not a certified one. The paper says this. Closing the gap, probably by perturbing the point set before building the topology rather than perturbing the topology afterwards, is the most valuable follow-on problem.

---

## 4. Why This Is Publishable

### The honest case

1. **A real literature gap.** Three bodies of work (pathology graph representations, graph inversion attacks, structural graph DP) have never been combined. The combination produces the structural ceiling, which has no analogue in the social-graph DP literature because those papers have no upstream image to protect.

2. **A derived rather than assumed degree bound.** This fixes the standard weakness of node-DP and it is specific to your domain. Reviewers reward assumptions that are discharged.

3. **A counterintuitive, quotable result.** Higher scanner resolution strictly improves privacy. That is memorable and it is provable.

4. **A negative result about your own framework.** Papers that only confirm their own thesis read as marketing. Showing that abstraction alone fails against linkage, quantifying the failure at 42× chance, and then showing what fixes it is the difference between a plausible paper and a credible one.

5. **Full numerical verification.** Every bound tested by brute force, three shown exactly tight, the degeneracy of your weakest lemma confirmed rather than hidden. Theory papers with this level of self-checking are uncommon.

6. **No adoption cost.** Pathology already moved to cell graphs for accuracy reasons (Pati et al., GrapHist). You are not asking anyone to trade accuracy for privacy.

### What would get it rejected, and the fix

| Risk | Fix, already applied |
|---|---|
| Reviewer knows cancelable biometrics and objects to the "new paradigm" framing | Reframe as first application to medical imaging with a quantified gap; do not claim to invent the paradigm |
| Reviewer checks the Fano corollary and finds it vacuous | Corrected; the per-patient bound is now explicitly identified as the operative one |
| Reviewer objects that Assumption 1 assumes the conclusion | Stated explicitly, $q$ kept visible in every constant, listed as a limitation |
| Reviewer asks for empirics from a theory paper | Now included: five experiments and five figures |
| Reviewer notices node-DP does not protect patients in the intra-slide regime | Now stated as an explicit open problem with the measured 31.6× cost |

### Venue positioning

Given the negative result and the numerical study, the natural targets are:

- **MICCAI or IPMI**, because there is now an experimental section and the clinical framing is strong.
- **PETS (Privacy Enhancing Technologies Symposium)**, the best fit for the linkage-versus-reconstruction distinction.
- **IEEE TIFS**, if you want a journal and are willing to extend the empirical work to real slides.

I would not target a pure information theory venue with this version, because Lemma A is the weakest result and it is the one that community would scrutinise most.

---

## 5. Reproducing Everything

```bash
cd sim
python exp1_sensitivity.py      # sensitivity bounds, packing, worked example
python exp2_reidentification.py # single-view linkage (degenerate baseline)
python exp3_reid_twoview.py     # two-view linkage, the headline experiment
python exp4_theorems.py         # Theorems 1 and 2, Lemma A regimes, separation
python make_figures.py          # all five figures
```

Results are written to `sim/results_exp*.json` and figures to `figs/`. All seeds are fixed. Total runtime is roughly three minutes.

**A note on Experiment 2 versus Experiment 3.** Experiment 2 is retained deliberately as a methodological illustration. In it, the probe vector is a noisy copy of the very vector in the gallery, so at zero noise matching is trivially 100% and tells you nothing about biometric content. Experiment 3 fixes this by using an independent second acquisition, and it is the one you should cite. If a reviewer asks whether your re-identification protocol is sound, this distinction is the answer.
