#!/usr/bin/env python3
"""
Compares the deployed app's actual Wells Expanded Criteria Pathway output
(app_results.json, produced by driving the real UI with Playwright) against
an independent from-scratch Python reference implementation of the same
documented algorithm (patients.json, produced by generate_reference.py).

This measures whether the shipped JavaScript correctly implements its own
documented decision rules across a large, varied set of synthetic cases --
i.e. an implementation-correctness / regression check, not a clinical
accuracy claim. These are randomly generated synthetic patients with no
real-world diagnosis, so there is no ground-truth PE status to validate
against; "accuracy" here means agreement with the algorithm as documented.

Writes VALIDATION_REPORT.md and results.csv.
"""

import json
import csv

with open("patients.json") as f:
    patients = {p["id"]: p for p in json.load(f)}
with open("app_results.json") as f:
    app_results = {r["id"]: r for r in json.load(f)}

TIERS = ["low", "moderate", "high"]

rows = []
errored = []
for pid, p in patients.items():
    ref = p["reference"]["pretest"]
    ar = app_results.get(pid)
    if ar is None:
        errored.append((pid, "no app result"))
        continue
    if ar.get("error"):
        errored.append((pid, ar["error"]))
        continue
    app_pretest = ar["appPretest"]
    match = (app_pretest == ref)
    rows.append({
        "id": pid,
        "age": p["age"],
        "sex": p["sex"],
        "category": p["reference"]["category"],
        "altDx": p["altDx"],
        "riskPresent": p["reference"]["riskPresent"],
        "respCount": p["reference"]["respCount"],
        "severeCriteria": p["reference"]["severeCriteria"],
        "reference_pretest": ref,
        "app_pretest": app_pretest,
        "match": match,
    })

n_total = len(rows) + len(errored)
n_scored = len(rows)
n_match = sum(1 for r in rows if r["match"])
accuracy = (n_match / n_scored * 100) if n_scored else 0.0

# Confusion matrix
confusion = {t: {t2: 0 for t2 in TIERS} for t in TIERS}
for r in rows:
    confusion[r["reference_pretest"]][r["app_pretest"]] += 1

# Breakdown by category (severe/typical/atypical)
by_category = {}
for r in rows:
    c = r["category"]
    by_category.setdefault(c, {"n": 0, "match": 0})
    by_category[c]["n"] += 1
    by_category[c]["match"] += 1 if r["match"] else 0

mismatches = [r for r in rows if not r["match"]]

with open("results.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

lines = []
lines.append("# Wells Expanded Criteria Pathway — 400-Patient Validation Report\n")
lines.append(
    "This validates whether the deployed `index.html` app's Wells Expanded "
    "Criteria Pathway (Steps 1-3: cardiopulmonary symptoms -> vitals/exam/CXR/EKG "
    "-> clinical judgment) computes the same pretest probability as an "
    "independent, from-scratch Python re-implementation of the same documented "
    "algorithm (`generate_reference.py`), for 400 randomly generated synthetic "
    "adult patients spanning a variety of ages, sexes, symptom combinations, "
    "exam/EKG findings, VTE risk factors, and clinical-judgment calls.\n"
)
lines.append(
    "**Important scope note:** these are synthetic, randomly generated patients "
    "with no real-world diagnosis, so there is no ground-truth PE status to "
    "measure clinical accuracy against. \"Accuracy\" below means *agreement "
    "between the live app and the documented algorithm it's supposed to "
    "implement* — i.e., this is a software-correctness/regression check, "
    "confirming the shipped JavaScript has no bugs relative to its own spec, "
    "not a claim about diagnostic performance. Age and sex were generated for "
    "demographic variety but are not used by this pathway's pretest-probability "
    "logic (they only matter later, at the PERC step, which is outside this "
    "run's scope).\n"
)
lines.append(f"## Result\n")
lines.append(f"**{n_match} / {n_scored} patients matched ({accuracy:.1f}% agreement)**")
if errored:
    lines.append(f", {len(errored)} patient(s) errored during the UI run (see below).")
lines.append("\n")

lines.append("## Confusion matrix (reference row vs. app column)\n")
lines.append("| Reference \\ App | Low | Moderate | High |")
lines.append("|---|---|---|---|")
for t in TIERS:
    row = confusion[t]
    lines.append(f"| **{t.capitalize()}** | {row['low']} | {row['moderate']} | {row['high']} |")
lines.append("")

lines.append("## Agreement by presentation category\n")
lines.append("| Category | N | Matched | Agreement |")
lines.append("|---|---|---|---|")
for c in ["severe", "typical", "atypical"]:
    if c in by_category:
        n = by_category[c]["n"]
        m = by_category[c]["match"]
        lines.append(f"| {c.capitalize()} | {n} | {m} | {m/n*100:.1f}% |")
lines.append("")

lines.append("## Pretest probability distribution (reference)\n")
dist = {t: sum(1 for r in rows if r["reference_pretest"] == t) for t in TIERS}
lines.append("| Tier | N |")
lines.append("|---|---|")
for t in TIERS:
    lines.append(f"| {t.capitalize()} | {dist[t]} |")
lines.append("")

if mismatches:
    lines.append(f"## Mismatches ({len(mismatches)})\n")
    lines.append("| ID | Age | Sex | Category | AltDx | Risk present | Reference | App |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in mismatches:
        lines.append(f"| {r['id']} | {r['age']} | {r['sex']} | {r['category']} | {r['altDx']} | {r['riskPresent']} | {r['reference_pretest']} | {r['app_pretest']} |")
    lines.append("")
else:
    lines.append("## Mismatches\n\nNone.\n")

if errored:
    lines.append(f"## Errors ({len(errored)})\n")
    for pid, msg in errored:
        lines.append(f"- Patient {pid}: {msg}")
    lines.append("")

lines.append("## Files\n")
lines.append("- `patients.json` — the 400 generated patients plus each one's reference-implementation output.")
lines.append("- `app_results.json` — what the live app actually returned for each patient.")
lines.append("- `results.csv` — per-patient comparison, one row each.")
lines.append("- `generate_reference.py`, `run_app_validation.js`, `compare_results.py` — the scripts that produced this report; rerun in that order to reproduce (seed is fixed, so patients.json is deterministic).")

with open("VALIDATION_REPORT.md", "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"{n_match}/{n_scored} matched ({accuracy:.1f}%), {len(errored)} errored.")
print("Wrote VALIDATION_REPORT.md and results.csv")
