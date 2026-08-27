# Wells Expanded Criteria Pathway — 400-Patient Validation Report

This validates whether the deployed `index.html` app's Wells Expanded Criteria Pathway (Steps 1-3: cardiopulmonary symptoms -> vitals/exam/CXR/EKG -> clinical judgment) computes the same pretest probability as an independent, from-scratch Python re-implementation of the same documented algorithm (`generate_reference.py`), for 400 randomly generated synthetic adult patients spanning a variety of ages, sexes, symptom combinations, exam/EKG findings, VTE risk factors, and clinical-judgment calls.

**Important scope note:** these are synthetic, randomly generated patients with no real-world diagnosis, so there is no ground-truth PE status to measure clinical accuracy against. "Accuracy" below means *agreement between the live app and the documented algorithm it's supposed to implement* — i.e., this is a software-correctness/regression check, confirming the shipped JavaScript has no bugs relative to its own spec, not a claim about diagnostic performance. Age and sex were generated for demographic variety but are not used by this pathway's pretest-probability logic (they only matter later, at the PERC step, which is outside this run's scope).

## Result

**400 / 400 patients matched (100.0% agreement)**


## Confusion matrix (reference row vs. app column)

| Reference \ App | Low | Moderate | High |
|---|---|---|---|
| **Low** | 115 | 0 | 0 |
| **Moderate** | 0 | 145 | 0 |
| **High** | 0 | 0 | 140 |

## Agreement by presentation category

| Category | N | Matched | Agreement |
|---|---|---|---|
| Severe | 105 | 105 | 100.0% |
| Typical | 121 | 121 | 100.0% |
| Atypical | 174 | 174 | 100.0% |

## Pretest probability distribution (reference)

| Tier | N |
|---|---|
| Low | 115 |
| Moderate | 145 |
| High | 140 |

## Mismatches

None.

## Files

- `patients.json` — the 400 generated patients plus each one's reference-implementation output.
- `app_results.json` — what the live app actually returned for each patient.
- `results.csv` — per-patient comparison, one row each.
- `generate_reference.py`, `run_app_validation.js`, `compare_results.py` — the scripts that produced this report; rerun in that order to reproduce (seed is fixed, so patients.json is deterministic).
