# Guideline-Anchored Golden Case Report

100 hand-built clinical vignettes whose expected recommendation is taken from the primary literature and the 2026 AHA/ACC PE guideline — **not** from `index.html`. Each case carries the citation that dictates its answer, in `cases.json`.

Unlike `validation_200/`, which compares the app against a transcription of its own logic, these cases can fail because the app is *clinically* wrong rather than merely self-inconsistent. See `build_cases.py` for what each case can and cannot anchor.

## Result

**89 / 89 binding cases passed (100.0%)**.

11 advisory cases (cited authorities conflict, or the guideline endorses an option the app documents it does not implement) are listed separately and excluded from this figure.

## Binding cases by rule under test

| Rule | N | Passed |
|---|---|---|
| PERC rule-out (PERC 0/8 at low probability) | 11 | 11 |
| YEARS-adjusted D-dimer, threshold 1000 | 40 | 40 |
| YEARS-adjusted D-dimer, threshold 500 | 27 | 27 |
| High probability → CTPA directly | 11 | 11 |

## Failures (0)

None.

## Advisory cases (11)

These record what the app does where the cited authorities disagree or where an endorsed alternative is out of scope. They are for clinical review, not pass/fail.

| # | Vignette | App behavior | Matches the app's cited basis? | Issue |
|---|---|---|---|---|
| 58 | 69M, high gestalt probability, SBP 78 with HR 124 — shock criteria met. | bedside_tte | yes | Cited authorities conflict: 2019 ESC supports bedside echocardiography in the unstable patient when CTPA is not immediately available, while the 2026 AHA/ACC guideline assigns echocardiography Class 3 (No Benefit) for confirming or refuting PE. The app follows ESC and says CTPA remains the study of choice. Reviewed as a design decision, not scored as a defect. |
| 59 | 74F, high probability, SBP 84, mechanically ventilated. | bedside_tte | yes | Cited authorities conflict: 2019 ESC supports bedside echocardiography in the unstable patient when CTPA is not immediately available, while the 2026 AHA/ACC guideline assigns echocardiography Class 3 (No Benefit) for confirming or refuting PE. The app follows ESC and says CTPA remains the study of choice. Reviewed as a design decision, not scored as a defect. |
| 60 | 61M, high probability, SBP 86 on FiO2 60% to maintain saturation. | bedside_tte | yes | Cited authorities conflict: 2019 ESC supports bedside echocardiography in the unstable patient when CTPA is not immediately available, while the 2026 AHA/ACC guideline assigns echocardiography Class 3 (No Benefit) for confirming or refuting PE. The app follows ESC and says CTPA remains the study of choice. Reviewed as a design decision, not scored as a defect. |
| 61 | 57F, high probability, SBP 88 but HR 84, not ventilated, FiO2 30%. | ctpa_direct | yes | The app requires SBP <90 PLUS one of tachycardia / ventilation / FiO2 >=40%. Isolated hypotension is treated as stable. Worth reviewing against local practice. |
| 62 | 71M, syncope with SBP 82 and HR 118; alternative diagnosis less likely. | bedside_tte | yes | Cited authorities conflict: 2019 ESC supports bedside echocardiography in the unstable patient when CTPA is not immediately available, while the 2026 AHA/ACC guideline assigns echocardiography Class 3 (No Benefit) for confirming or refuting PE. The app follows ESC and says CTPA remains the study of choice. Reviewed as a design decision, not scored as a defect. |
| 63 | 64F, high tier, SBP 85, HR 112, alternative diagnosis less likely. | bedside_tte | yes | Cited authorities conflict: 2019 ESC supports bedside echocardiography in the unstable patient when CTPA is not immediately available, while the 2026 AHA/ACC guideline assigns echocardiography Class 3 (No Benefit) for confirming or refuting PE. The app follows ESC and says CTPA remains the study of choice. Reviewed as a design decision, not scored as a defect. |
| 96 | 78M, intermediate probability, DVT signs, D-dimer 700 (below age-adjusted 780, above 500). | ddimer_imaging | yes | The 2026 AHA/ACC guideline lists an age-adjusted threshold (age x 10 ug/L FEU for patients >50) as a Class 2a alternative. The app applies the YEARS adjustment only, so for an older patient with >=1 YEARS item it uses 500 where age adjustment would allow a higher cut-off. Both strategies are endorsed; this is a documented scope choice, not a defect. |
| 97 | 85F, intermediate probability, PE most likely, D-dimer 800 (below age-adjusted 850). | ddimer_imaging | yes | The 2026 AHA/ACC guideline lists an age-adjusted threshold (age x 10 ug/L FEU for patients >50) as a Class 2a alternative. The app applies the YEARS adjustment only, so for an older patient with >=1 YEARS item it uses 500 where age adjustment would allow a higher cut-off. Both strategies are endorsed; this is a documented scope choice, not a defect. |
| 98 | 66M, intermediate probability, hemoptysis, D-dimer 640 (below age-adjusted 660). | ddimer_imaging | yes | The 2026 AHA/ACC guideline lists an age-adjusted threshold (age x 10 ug/L FEU for patients >50) as a Class 2a alternative. The app applies the YEARS adjustment only, so for an older patient with >=1 YEARS item it uses 500 where age adjustment would allow a higher cut-off. Both strategies are endorsed; this is a documented scope choice, not a defect. |
| 99 | 80F, moderate tier, PE most likely, D-dimer 750 (below age-adjusted 800). | ddimer_imaging | yes | The 2026 AHA/ACC guideline lists an age-adjusted threshold (age x 10 ug/L FEU for patients >50) as a Class 2a alternative. The app applies the YEARS adjustment only, so for an older patient with >=1 YEARS item it uses 500 where age adjustment would allow a higher cut-off. Both strategies are endorsed; this is a documented scope choice, not a defect. |
| 100 | 72M, moderate tier with leg swelling, D-dimer 690 (below age-adjusted 720). | ddimer_imaging | yes | The 2026 AHA/ACC guideline lists an age-adjusted threshold (age x 10 ug/L FEU for patients >50) as a Class 2a alternative. The app applies the YEARS adjustment only, so for an older patient with >=1 YEARS item it uses 500 where age adjustment would allow a higher cut-off. Both strategies are endorsed; this is a documented scope choice, not a defect. |

## Files

- `build_cases.py` — builds `cases.json`; holds every expected answer as a literal, with its citation.
- `cases.json` — the 100 cases.
- `run_golden_cases.js` — drives the real UI and writes this report plus `golden_results.csv`.
