#!/usr/bin/env python3
"""
Compares the deployed app's end-to-end recommendation (app_results.json,
produced by driving the real UI with Playwright) against the independent
from-scratch Python reference implementation (patients.json, produced by
generate_reference.py), for 200 synthetic patients split evenly between the
Wells Expanded Criteria Pathway and the Clinical Gestalt Pathway.

The headline number is recommendation accuracy: does the app suggest the
same next test as the documented algorithm? Intermediate stages (pretest
probability, PERC score, YEARS-adjusted D-dimer threshold) are scored
separately so a mismatch can be attributed to the stage that caused it.

Writes VALIDATION_REPORT.md and results.csv.
"""

import json
import csv

with open("patients.json") as f:
    patients = {p["id"]: p for p in json.load(f)}
with open("app_results.json") as f:
    app_results = {r["id"]: r for r in json.load(f)}

RECS = ["none_perc_negative", "ddimer_ruled_out", "ddimer_imaging", "ctpa_direct", "bedside_tte"]
REC_LABEL = {
    "none_perc_negative": "No further testing (PERC 0/8)",
    "ddimer_ruled_out": "D-dimer below threshold — PE ruled out",
    "ddimer_imaging": "D-dimer at/above threshold — CTPA",
    "ctpa_direct": "CTPA directly (high probability)",
    "bedside_tte": "Bedside TTE (unstable)",
}
# The app calls the gestalt pathway's middle tier "intermediate" and the Wells
# pathway's "moderate"; they are the same tier for comparison purposes.
TIER_ALIAS = {"moderate": "moderate", "intermediate": "moderate", "low": "low", "high": "high"}

rows = []
errored = []
for pid, p in patients.items():
    ref = p["reference"]
    ar = app_results.get(pid)
    if ar is None:
        errored.append((pid, "no app result"))
        continue
    if ar.get("error"):
        errored.append((pid, ar["error"]))
        continue
    rows.append({
        "id": pid,
        "pathway": p["pathway"],
        "age": p["age"],
        "sex": p["sex"],
        "ddimer": p["ddimer"],
        "reference_pretest": TIER_ALIAS[ref["pretest"]],
        "app_pretest": TIER_ALIAS[ar["appPretest"]],
        "pretest_match": TIER_ALIAS[ref["pretest"]] == TIER_ALIAS[ar["appPretest"]],
        "reference_perc": ref["percScore"],
        "app_perc": ar["appPercScore"],
        "perc_match": ref["percScore"] == ar["appPercScore"],
        "reference_threshold": ref["threshold"],
        "app_threshold": ar["appThreshold"],
        "threshold_match": ref["threshold"] == ar["appThreshold"],
        "reference_recommendation": ref["recommendation"],
        "app_recommendation": ar["appRecommendation"],
        "match": ref["recommendation"] == ar["appRecommendation"],
    })

n_scored = len(rows)
n_match = sum(1 for r in rows if r["match"])
accuracy = (n_match / n_scored * 100) if n_scored else 0.0
mismatches = [r for r in rows if not r["match"]]

stage_acc = {}
for stage, key in [("Pretest probability", "pretest_match"),
                   ("PERC score", "perc_match"),
                   ("D-dimer threshold", "threshold_match"),
                   ("Final recommendation", "match")]:
    applicable = [r for r in rows if not (
        (key == "perc_match" and r["reference_perc"] is None and r["app_perc"] is None) or
        (key == "threshold_match" and r["reference_threshold"] is None and r["app_threshold"] is None)
    )]
    matched = sum(1 for r in applicable if r[key])
    stage_acc[stage] = (matched, len(applicable))

by_pathway = {}
for r in rows:
    d = by_pathway.setdefault(r["pathway"], {"n": 0, "match": 0})
    d["n"] += 1
    d["match"] += 1 if r["match"] else 0

confusion = {a: {b: 0 for b in RECS} for a in RECS}
for r in rows:
    confusion[r["reference_recommendation"]][r["app_recommendation"]] += 1

with open("results.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

L = []
L.append("# 200-Patient End-to-End Recommendation Validation\n")
L.append(
    "This validates whether the deployed `index.html` app suggests the same **next "
    "diagnostic test** as an independent, from-scratch Python re-implementation of "
    "its own documented algorithm (`generate_reference.py`), for 200 randomly "
    "generated synthetic adult patients — 100 routed through the Wells Expanded "
    "Criteria Pathway and 100 through the Clinical Gestalt Pathway.\n"
)
L.append(
    "Unlike `validation_400/`, which stops at pretest probability, this run scores "
    "the full pipeline end to end: pretest probability → PERC → the YEARS-adjusted "
    "D-dimer threshold → the measured D-dimer's interpretation → the final recommended "
    "test. The Playwright driver never predicts the route; it clicks whatever "
    "*Continue* button the app presents and records which screen it lands on, so the "
    "route is the app's answer rather than an assumption in the harness.\n"
)
L.append(
    "**Important scope note:** these are synthetic, randomly generated patients with "
    "no real-world diagnosis, so there is no ground-truth PE status. \"Accuracy\" "
    "below means *agreement between the live app and the documented algorithm it is "
    "supposed to implement* — a software-correctness/regression check, not a claim "
    "about diagnostic performance.\n"
)

L.append("## Result\n")
L.append(f"**{n_match} / {n_scored} patients received the correct recommendation ({accuracy:.1f}% agreement)**")
if errored:
    L.append(f", {len(errored)} patient(s) errored during the UI run (see below).")
L.append("\n")

L.append("## Agreement by stage\n")
L.append("| Stage | N applicable | Matched | Agreement |")
L.append("|---|---|---|---|")
for stage, (m, n) in stage_acc.items():
    L.append(f"| {stage} | {n} | {m} | {m/n*100:.1f}% |" if n else f"| {stage} | 0 | 0 | — |")
L.append("")

L.append("## Agreement by pathway\n")
L.append("| Pathway | N | Matched | Agreement |")
L.append("|---|---|---|---|")
for key, label in [("wells", "Wells Expanded Criteria"), ("gestalt", "Clinical Gestalt")]:
    if key in by_pathway:
        d = by_pathway[key]
        L.append(f"| {label} | {d['n']} | {d['match']} | {d['match']/d['n']*100:.1f}% |")
L.append("")

L.append("## Recommendation confusion matrix (reference row vs. app column)\n")
L.append("| Reference \\ App | " + " | ".join(REC_LABEL[r] for r in RECS) + " |")
L.append("|---" * (len(RECS) + 1) + "|")
for a in RECS:
    L.append(f"| **{REC_LABEL[a]}** | " + " | ".join(str(confusion[a][b]) for b in RECS) + " |")
L.append("")

L.append("## Recommendation distribution (reference)\n")
L.append("| Recommendation | N |")
L.append("|---|---|")
for r in RECS:
    L.append(f"| {REC_LABEL[r]} | {sum(1 for x in rows if x['reference_recommendation'] == r)} |")
L.append("")

L.append("## D-dimer threshold selection\n")
thr = {}
for r in rows:
    if r["reference_threshold"] is not None:
        d = thr.setdefault(r["reference_threshold"], {"n": 0, "match": 0})
        d["n"] += 1
        d["match"] += 1 if r["threshold_match"] else 0
L.append("| Threshold (ng/mL FEU) | N | Matched |")
L.append("|---|---|---|")
for t in sorted(thr):
    L.append(f"| <{t} | {thr[t]['n']} | {thr[t]['match']} |")
L.append("")

if mismatches:
    L.append(f"## Mismatches ({len(mismatches)})\n")
    L.append("| ID | Pathway | Ref pretest | App pretest | Ref PERC | App PERC | Ref threshold | App threshold | D-dimer | Reference | App |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in mismatches:
        L.append("| {id} | {pathway} | {reference_pretest} | {app_pretest} | {reference_perc} | {app_perc} | "
                 "{reference_threshold} | {app_threshold} | {ddimer} | {reference_recommendation} | "
                 "{app_recommendation} |".format(**r))
    L.append("")
else:
    L.append("## Mismatches\n\nNone.\n")

if errored:
    L.append(f"## Errors ({len(errored)})\n")
    for pid, msg in errored:
        L.append(f"- Patient {pid}: {msg}")
    L.append("")

L.append("## Files\n")
L.append("- `patients.json` — the 200 generated patients plus each one's reference-implementation output.")
L.append("- `app_results.json` — the app's pretest tier, PERC score, threshold, route and final recommendation for each patient.")
L.append("- `results.csv` — per-patient comparison, one row each.")
L.append("- `generate_reference.py`, `run_app_validation.js`, `compare_results.py` — the scripts that produced this report; rerun in that order to reproduce (seed is fixed, so patients.json is deterministic).")

with open("VALIDATION_REPORT.md", "w") as f:
    f.write("\n".join(L) + "\n")

print(f"{n_match}/{n_scored} recommendations matched ({accuracy:.1f}%), {len(errored)} errored.")
for stage, (m, n) in stage_acc.items():
    print(f"  {stage}: {m}/{n}")
print("Wrote VALIDATION_REPORT.md and results.csv")
