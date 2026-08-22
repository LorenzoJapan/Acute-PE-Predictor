# Acute PE Predictor

An iOS-styled clinical decision-support prototype for suspected acute pulmonary embolism (PE). It walks through a three-step assessment to arrive at a pretest probability (Low / Moderate / High), then routes to the appropriate D-dimer threshold or straight to imaging.

**Live demo:** https://claude.ai/code/artifact/329b1525-4fc4-42c4-bbdd-902463818535

## What it does

1. **Cardiopulmonary symptoms** — respiratory findings, syncope.
2. **Vitals, P/E, CXR & EKG findings** — vitals, physical exam, chest X-ray findings, EKG findings.
3. **Clinical judgment** — alternative diagnosis assessment, VTE risk factors.

From there the app computes a pretest probability and applies the matching next step:

| Pretest probability | Next step |
|---|---|
| Low | D-dimer, ruled out if < 1000 ng/mL |
| Moderate | D-dimer, ruled out if < 500 ng/mL |
| High | Proceed directly to chest imaging (CT pulmonary angiography) |

## Clinical basis

- Wells PS, Ginsberg JS, Anderson DR, Kearon C, Turpie AG, Bormanis J, et al. Use of a clinical model for safe management of patients with suspected pulmonary embolism. *Ann Intern Med.* 1998;129(12):997-1005.
- Kearon C, de Wit K, Parpia S, Schulman S, Afilalo M, Hirsch A, et al. Diagnosis of pulmonary embolism with D-dimer adjusted to clinical probability. *N Engl J Med.* 2019;381(22):2125-2134.

Full citations and methodology notes are also shown in-app, under "About this tool & sources" on the home screen.

## Files

- `index.html` — the complete app (single-file HTML/CSS/JS, no build step, no dependencies). Open it directly in a browser.
- `validation/test_harness.js` — a Node.js regression test that runs 100 synthetic patients (including deliberate boundary cases) through the app's decision logic and an independently written reference implementation, and reports agreement. Run with `node validation/test_harness.js`.
- `validation/VALIDATION_REPORT.md` — write-up of the validation methodology, results (100/100 agreement as of the last run), and its scope/limitations.
- `validation/results.csv` — the per-patient inputs and outputs from the last validation run.

## Running it

No build step. Open `index.html` in a browser, or serve the folder with any static file server.

## ⚠️ Medical disclaimer

This is a **design and interaction prototype**. It has not been validated as a medical device, has not undergone clinical or regulatory review, and should not be used to guide patient care. Verify all logic against your institution's protocol and current literature before any clinical use.

## License

MIT — see [LICENSE](LICENSE).
