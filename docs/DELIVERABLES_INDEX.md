# DELIVERABLES — What to use (meeting pack)

Everything important is copied here so you can ignore the messy project root.
Originals still exist upstairs; this folder is the clean focus set.

---

## Start here for tomorrow’s meeting

| Order | Open this | Why |
|---|---|---|
| 1 | `reports/WORKING_FACTOR_GATE.md` | Pass/fail on real PanNuke |
| 2 | `figures/fig_pannuke_privacy_utility.png` | The plot to show |
| 3 | `papers/Privacy_Representation_Springer.docx` | Current paper draft (Word) |
| 4 | `reports/RESULTS_BRIEFING.md` | Short email-style summary |
| 5 | `papers/Project_Proposal.docx` | Work plan / timeline if asked |

---

## Folder map

### `papers/`
- **`Privacy_Representation_Springer.docx`** — main draft to discuss (Springer proceedings style)
- **`springer_main.pdf`** — LNCS LaTeX PDF version
- **`APA_theory_draft.pdf`** — longer APA theory draft (`main.pdf`)
- **`Project_Proposal.docx`** — supervisor proposal

### `reports/`
- **`WORKING_FACTOR_GATE.md`** — publication gate (PASSED)
- **`RESULTS_BRIEFING.md`** — 1-page results briefing
- **`FINDINGS_AND_NOVELTY.md`** — novelty grading + findings
- **`PAPER_EXPLAINED.md`** — A–Z explanation of the paper (for you)

### `figures/`
- **`fig_pannuke_privacy_utility.*`** — real-data privacy vs utility (**show this**)
- **`fig_pannuke_geometry.*`** — nuclear separation on PanNuke
- **`fig_privacy_utility.*`** — synthetic version (comparison)
- **`fig_ceiling.*`**, **`fig_lemma_a.*`**, etc. — theory support plots

### `sim_code/`
Runnable experiment scripts (copy of `sim/`). To re-run, better use the original `sim/` folder in the project root (paths expect that layout). This copy is for reference / backup.

### `sim_results/`
- JSON outputs from synthetic + PanNuke experiments
- **`processed_cells.npz`** — compact PanNuke cell layouts used in experiments

### `format_templates/`
Springer Word template + instructions (for final style polish).

---

## One-sentence project reminder

Graphs preserve diagnosis but not identity; DP noise is required; on PanNuke a usable window is around **ε ∈ [5, 10]**; theory bounds checked with **0 sensitivity violations**.

---

## Do not submit from here without

1. Filling author / affiliation in the `.docx`
2. Optional: paste into `format_templates/splnproc2510.docm`, apply ribbon styles, Save As `.docx`
3. Supervisor sign-off on venue
