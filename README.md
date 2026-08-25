# Acute PE Predictor

An iOS-styled clinical decision-support prototype for suspected acute pulmonary embolism (PE). It walks through a three-step assessment to arrive at a pretest probability (Low / Moderate / High), then routes to PERC screening, a YEARS-adjusted D-dimer threshold, or straight to imaging.

**Live demo:** https://claude.ai/code/artifact/329b1525-4fc4-42c4-bbdd-902463818535

## What it does

1. **Cardiopulmonary symptoms** — respiratory findings, syncope.
2. **Vitals, P/E, CXR & EKG findings** — vitals, physical exam, chest X-ray findings, EKG findings.
3. **Clinical judgment** — alternative diagnosis assessment, VTE risk factors.

From there the app computes a pretest probability and applies the matching next step:

| Pretest probability | Next step |
|---|---|
| Low | PERC screened first. All 8 criteria negative → PE excluded, no D-dimer needed. Any positive → D-dimer, ruled out if < 1000 ng/mL |
| Moderate | D-dimer threshold set by YEARS items (signs of DVT, hemoptysis, PE most likely diagnosis): 0 items → < 1000 ng/mL; ≥1 item → < 500 ng/mL |
| High | Proceed directly to chest imaging (CT pulmonary angiography) — or, if hemodynamically unstable (shock criteria met), bedside TTE if the patient can't be safely transported for CTPA |

PERC and YEARS are layered onto the existing three-step flow rather than adding new questions up front: PERC only appears once a patient is scored Low (five of its eight items are reused from Steps 1–3; only age, estrogen use, and recent surgery/trauma are asked fresh), and YEARS reuses three items already captured in Steps 1–3 with no new screen at all for Moderate-probability patients. Likewise, the high-probability instability check reuses the app's existing shock calculation (SBP <90 mmHg with tachycardia, mechanical ventilation, or a high oxygen requirement) rather than asking anything new — it only changes what the Final screen recommends.

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
- `validation_400/` — an independent 400-synthetic-patient validation of the app's pretest-probability, PERC, and YEARS logic:
  - `generate_reference.py` — generates 400 randomized patients and scores each with a from-scratch Python reference implementation of the app's documented decision rules, plus the classic published Wells score as an external benchmark. Deterministic (fixed seed). Run with `python3 generate_reference.py`.
  - `run_app_validation.js` — drives the actual deployed `index.html` (headless Chromium via Playwright) for every generated patient and records what the app itself computes. Run with `node run_app_validation.js` (~2 minutes for 400 patients).
  - `compare_results.py` — compares the app's outputs against the reference implementation and the classic Wells score; writes `VALIDATION_REPORT.md` and `results.csv`. Run with `python3 compare_results.py`.
  - `patients.json`, `app_results.json` — raw inputs/outputs from the last run, kept for reproducibility.
  - `VALIDATION_REPORT.md`, `results.csv` — the last run's report (400/400 agreement with the independent reference implementation) and per-patient detail.

> **Note:** an earlier `validation/` folder (`test_harness.js`, 100 synthetic patients) predates the PERC and YEARS logic and is not included here — `validation_400/` supersedes it and covers the current decision logic, including PERC and YEARS.

## Running it

No build step. Open `index.html` in a browser, or serve the folder with any static file server.

## ⚠️ Medical Disclaimer

This application is a clinical decision support tool intended to help licensed healthcare professionals organize and evaluate clinical information. It does not diagnose, treat, cure, or prevent any disease, and its outputs are not a substitute for clinical judgment. All recommendations must be independently reviewed against the underlying data by the treating clinician before any decision is made, and final responsibility for patient care rests with the provider. This tool is intended for use by licensed healthcare professionals only and is not intended for use by patients or caregivers for self-diagnosis or self-treatment, or for emergency or life-threatening situations. It has not been cleared or approved by the FDA.

## License

MIT — see [LICENSE](LICENSE).
