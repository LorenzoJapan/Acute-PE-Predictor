# 200-Patient End-to-End Recommendation Validation

This validates whether the deployed `index.html` app suggests the same **next diagnostic test** as an independent, from-scratch Python re-implementation of its own documented algorithm (`generate_reference.py`), for 200 randomly generated synthetic adult patients — 100 routed through the Wells Expanded Criteria Pathway and 100 through the Clinical Gestalt Pathway.

Unlike `validation_400/`, which stops at pretest probability, this run scores the full pipeline end to end: pretest probability → PERC → the YEARS-adjusted D-dimer threshold → the measured D-dimer's interpretation → the final recommended test. The Playwright driver never predicts the route; it clicks whatever *Continue* button the app presents and records which screen it lands on, so the route is the app's answer rather than an assumption in the harness.

**Important scope note:** these are synthetic, randomly generated patients with no real-world diagnosis, so there is no ground-truth PE status. "Accuracy" below means *agreement between the live app and the documented algorithm it is supposed to implement* — a software-correctness/regression check, not a claim about diagnostic performance.

## Result

**200 / 200 patients received the correct recommendation (100.0% agreement)**


## Agreement by stage

| Stage | N applicable | Matched | Agreement |
|---|---|---|---|
| Pretest probability | 200 | 200 | 100.0% |
| PERC score | 60 | 60 | 100.0% |
| D-dimer threshold | 118 | 118 | 100.0% |
| Final recommendation | 200 | 200 | 100.0% |

## Agreement by pathway

| Pathway | N | Matched | Agreement |
|---|---|---|---|
| Wells Expanded Criteria | 100 | 100 | 100.0% |
| Clinical Gestalt | 100 | 100 | 100.0% |

## Recommendation confusion matrix (reference row vs. app column)

| Reference \ App | No further testing (PERC 0/8) | D-dimer below threshold — PE ruled out | D-dimer at/above threshold — CTPA | CTPA directly (high probability) | Bedside TTE (unstable) |
|---|---|---|---|---|---|
| **No further testing (PERC 0/8)** | 6 | 0 | 0 | 0 | 0 |
| **D-dimer below threshold — PE ruled out** | 0 | 34 | 0 | 0 | 0 |
| **D-dimer at/above threshold — CTPA** | 0 | 0 | 84 | 0 | 0 |
| **CTPA directly (high probability)** | 0 | 0 | 0 | 59 | 0 |
| **Bedside TTE (unstable)** | 0 | 0 | 0 | 0 | 17 |

## Recommendation distribution (reference)

| Recommendation | N |
|---|---|
| No further testing (PERC 0/8) | 6 |
| D-dimer below threshold — PE ruled out | 34 |
| D-dimer at/above threshold — CTPA | 84 |
| CTPA directly (high probability) | 59 |
| Bedside TTE (unstable) | 17 |

## D-dimer threshold selection

| Threshold (ng/mL FEU) | N | Matched |
|---|---|---|
| <500 | 76 | 76 |
| <1000 | 42 | 42 |

## Mismatches

None.

## Files

- `patients.json` — the 200 generated patients plus each one's reference-implementation output.
- `app_results.json` — the app's pretest tier, PERC score, threshold, route and final recommendation for each patient.
- `results.csv` — per-patient comparison, one row each.
- `generate_reference.py`, `run_app_validation.js`, `compare_results.py` — the scripts that produced this report; rerun in that order to reproduce (seed is fixed, so patients.json is deterministic).
