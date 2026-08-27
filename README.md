# Acute PE Predictor

An iOS-styled clinical decision-support prototype for suspected acute pulmonary embolism (PE). From the home screen, choose how to reach a pretest probability — the **Wells Expanded Criteria Pathway** (a structured, stepwise assessment) or the **Clinical Gestalt Pathway** (a direct Low/Intermediate/High pick) — then both route through the same PERC, D-dimer, and imaging/TTE strategy.

**Live demo:** https://claude.ai/code/artifact/329b1525-4fc4-42c4-bbdd-902463818535 *(predates this pathway restructure — see below)*

## What it does

**Wells Expanded Criteria Pathway** — a three-step structured assessment: cardiopulmonary symptoms, then vitals/exam/CXR/EKG findings, then a clinical judgment of whether an alternative diagnosis is more, equally, or less likely than PE. These classify the presentation as typical, atypical, or severe, which combines with VTE risk factors (prior DVT/PE, recent immobilization or surgery, malignancy, estrogen use) to reach a Low, Moderate, or High pretest probability. It draws on the same elements as the classic Wells criteria (signs of DVT, heart rate, immobilization/surgery, prior VTE, hemoptysis, malignancy, alternative diagnosis less likely) expanded into a stepwise exam rather than a single point score. This is the app's original assessment flow (`#scr-resp` → `#scr-assoc` → `#scr-judgment` → `#scr-results` → `#scr-perc` → `#scr-ddimer` → `#scr-final`).

**Clinical Gestalt Pathway** — skip the structured steps and select Low (<15%), Intermediate (15–50%), or High (>50%) directly, based on overall clinical impression.

Either way, pretest probability then routes to the matching next step:

| Pretest probability | Next step |
|---|---|
| Low | PERC screened first. All 8 criteria negative → PE excluded, no D-dimer needed. Any positive → routes into the same D-dimer + YEARS step as Intermediate, below |
| Intermediate (and Low/PERC-positive) | D-dimer threshold set by YEARS items (signs of DVT, hemoptysis, PE most likely diagnosis): 0 items → < 1000 ng/mL; ≥1 item → < 500 ng/mL |
| High | Proceed directly to chest imaging (CT pulmonary angiography) — or, if hemodynamically unstable (shock criteria met), bedside TTE if the patient can't be safely transported for CTPA |

This matches Figure 1 of the 2026 AHA/ACC acute PE guideline: a PERC-positive low-probability patient and an intermediate-probability patient feed into the identical "Perform D-dimer testing and assess YEARS criteria" step, not separate thresholds.

On the Wells Expanded Criteria Pathway, PERC and YEARS items already captured during the symptoms/vitals/exam steps are carried over rather than asked twice (PERC reuses HR, hemoptysis, signs of DVT, and prior VTE; only age, estrogen use, and recent surgery/trauma are asked fresh). The Clinical Gestalt Pathway starts from nothing, so PERC and YEARS are asked fresh there instead. The High-probability shock assessment (SBP, HR, ventilation, FiO₂) is always asked fresh on both pathways, since neither collects vitals up front at that tier.

## Clinical basis

- Wells PS, Ginsberg JS, Anderson DR, Kearon C, Turpie AG, Bormanis J, et al. Use of a clinical model for safe management of patients with suspected pulmonary embolism. *Ann Intern Med.* 1998;129(12):997-1005.
- Kearon C, de Wit K, Parpia S, Schulman S, Afilalo M, Hirsch A, et al. Diagnosis of pulmonary embolism with D-dimer adjusted to clinical probability. *N Engl J Med.* 2019;381(22):2125-2134.
- Freund Y, Cachanado M, Aubry A, Orsini C, Raynal PA, Féral-Pierssens AL, et al. Effect of the pulmonary embolism rule-out criteria on subsequent thromboembolic events among low-risk emergency department patients: the PROPER randomized clinical trial. *JAMA.* 2018;319(6):559-566.
- van der Hulle T, Cheung WY, Kooij S, Beenen LFM, van Bemmel T, van Es J, et al. Simplified diagnostic management of suspected pulmonary embolism (the YEARS study): a prospective, multicentre, cohort study. *Lancet.* 2017;390(10091):289-297.
- Konstantinides SV, Meyer G, Becattini C, Bueno H, Geersing GJ, Harjola VP, et al. 2019 ESC Guidelines for the diagnosis and management of acute pulmonary embolism developed in collaboration with the European Respiratory Society (ERS). *Eur Heart J.* 2020;41(4):543-603.
- Creager MA, Barnes GD, Giri J, Mukherjee D, Jones WS, Burnett AE, et al. 2026 AHA/ACC/ACCP/ACEP/CHEST/SCAI/SHM/SIR/SVM/SVN guideline for the evaluation and management of acute pulmonary embolism in adults: a report of the American College of Cardiology/American Heart Association Joint Committee on Clinical Practice Guidelines. *Circulation.* 2026;153:e00-e00.

Full citations and methodology notes are also shown in-app, under "About this tool & sources" on the home screen.

## Files

- `index.html` — the complete app (single-file HTML/CSS/JS, no build step, no dependencies). Open it directly in a browser.
- `tests/test_flows.js` — a Playwright regression test driving the real UI through the PERC (low-probability), YEARS-adjusted (moderate-probability), and instability/bedside-TTE (high-probability) branches end to end (24 assertions). Run with `node tests/test_flows.js` (requires `playwright`).
- `tests/test_gw_flows.js` — a Playwright regression test for both home-screen pathways: the Wells Expanded Criteria Pathway driven end to end through the original structured-assessment screens, and the Clinical Gestalt Pathway across all three probability tiers, PERC negative/positive, YEARS thresholds, the bedside-TTE branch, and copy/restart. Run with `node tests/test_gw_flows.js`.
- `validation_400/` — an independent 400-synthetic-patient validation of the Wells Expanded Criteria Pathway's pretest-probability logic (Steps 1-3 only; does not cover PERC, YEARS, or D-dimer):
  - `generate_reference.py` — generates 400 randomized adult patients (varied ages, sexes, symptoms, vitals, exam/EKG findings, VTE risk factors, and clinical-judgment calls) and scores each with a from-scratch Python reference implementation of the app's documented decision rules. Deterministic (fixed seed). Run with `python3 generate_reference.py`.
  - `run_app_validation.js` — drives the actual deployed `index.html` (headless Chromium via Playwright) through the real UI for every generated patient and records what the app itself computes. Run with `node run_app_validation.js` (~18-20 minutes for 400 patients, since each patient clicks through the full 3-step UI).
  - `compare_results.py` — compares the app's outputs against the reference implementation; writes `VALIDATION_REPORT.md` and `results.csv`. Run with `python3 compare_results.py`.
  - `patients.json`, `app_results.json` — raw inputs/outputs from the last run, kept for reproducibility.
  - `VALIDATION_REPORT.md`, `results.csv` — the last run's report (400/400 agreement with the independent reference implementation) and per-patient detail.

Note that "accuracy" in this validation means agreement between the live app and its own documented algorithm (a correctness/regression check) — these are synthetic patients with no real diagnosis, so there's no clinical ground truth involved.

## Running it

No build step. Open `index.html` in a browser, or serve the folder with any static file server.

## ⚠️ Medical Disclaimer

This application is a clinical decision support tool intended to help licensed healthcare professionals organize and evaluate clinical information. It does not diagnose, treat, cure, or prevent any disease, and its outputs are not a substitute for clinical judgment. All recommendations must be independently reviewed against the underlying data by the treating clinician before any decision is made, and final responsibility for patient care rests with the provider. This tool is intended for use by licensed healthcare professionals only and is not intended for use by patients or caregivers for self-diagnosis or self-treatment, or for emergency or life-threatening situations. It has not been cleared or approved by the FDA.

## License

MIT — see [LICENSE](LICENSE).
