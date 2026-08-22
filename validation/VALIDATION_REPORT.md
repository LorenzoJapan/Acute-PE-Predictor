# Acute PE Predictor — Validation Test

## What this tests

The app's pretest-probability logic (respiratory-point counting, the typical/atypical/severe classification, and the alternative-diagnosis + risk-factor branch that produces Low/Moderate/High) was checked against an **independently written second implementation** of the same Wells 1998 (Figure 1) decision rules, run against **100 synthetic patients** with randomized clinical characteristics.

Two implementations, same 100 patients, same expected answer if the code is right:

1. **App logic** — copied verbatim from `compute()` and `autoShock()` in `index.html`, unchanged.
2. **Reference logic** — re-derived independently from the same published decision rules, but written as an explicit lookup table instead of nested if/else, so a copy-paste or control-flow slip in one wouldn't accidentally show up the same way in the other.

If both produce the same answer for all 100 patients, that's good evidence the app's code has no transcription bugs. A disagreement on any patient would point to the exact profile that exposes the bug.

## Patient generation

100 patients were generated with a fixed random seed (`20260822`), so this run is exactly reproducible — rerunning `test_harness.js` produces the identical 100 patients and the identical result. Each patient got randomized values for:

- The 6 respiratory-point findings (dyspnea, pleuritic chest pain, hemoptysis, atypical chest pain, pleural friction rub, chest X-ray), scattered between the two screens that can hold each item to exercise the cross-screen lookup.
- Syncope, low-grade fever, ventilation requirement, signs of DVT, elevated CVP, EKG findings.
- HR, SBP, room-air pulse ox, and FiO₂-to-correct — randomized across realistic ranges.
- The 8 VTE risk factors.
- The alternative-diagnosis judgment (as-likely / less-likely), 50/50.

Five patients (IDs 1–5) were deliberately set to **boundary values** — HR/SBP/pulse-ox/FiO₂ sitting exactly on or one unit past a `>`, `>=`, or `<` cutoff — since random sampling alone tends to under-test edges. This is standard practice for this kind of check, not a departure from "random": the other 95 are pure random draws.

## Results

| Metric | Value |
|---|---|
| Patients tested | 100 |
| Agreement (app vs. reference) | **100 / 100 (100.0%)** |
| Disagreements | 0 |

**Pretest probability distribution** (identical for both implementations, as expected given 100% agreement):

| Category | Count |
|---|---|
| Low | 15 |
| Moderate | 40 |
| High | 45 |

This distribution is skewed toward Moderate/High because the random generator gives each of the 8 risk factors a independent ~14% chance, so most synthetic patients end up with *at least one* risk factor present (~70% of the time) — that's an artifact of the test's randomization settings, not a claim about real-world PE prevalence. Don't read anything clinical into the 15/40/45 split; it only matters that the two implementations landed on the same split.

## What this does — and doesn't — validate

**Validates:** that the app's JavaScript correctly and consistently implements the decision logic exactly as it's documented and was worked through with you earlier in this session (respiratory-point counting, the typical/atypical/severe split, the severe/shock override, and the alternative-diagnosis + risk-factor branch table). Zero disagreements across 100 patients including boundary conditions is strong evidence there's no coding bug (inverted condition, off-by-one, wrong variable) in that logic.

**Does not validate:** that this reading of the original 1998 Wells figure is itself the one true correct interpretation. Both implementations encode the same interpretation of Figure 1 that was built into the app — a second implementation written from the same source will tend to reproduce the same reading, not catch a shared misreading of the original figure. That figure's exact branch structure isn't fully unambiguous from the published text alone (this came up directly earlier in this session, where two of my own verbal explanations of the branching were wrong before we settled on the table used here).

## Files

- `test_harness.js` — the test script (rerun anytime with `node test_harness.js` after future app changes; same seed reproduces the same 100 patients).
- `results.csv` — all 100 patients with both implementations' outputs, side by side, one row per patient.
