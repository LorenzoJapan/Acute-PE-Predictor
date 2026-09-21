#!/usr/bin/env python3
"""
Generates 400 randomized synthetic adult patients with varied demographics
and clinical findings, then scores each one with a from-scratch Python
reference implementation of the app's documented Wells Expanded Criteria
Pathway logic (Steps 1-3: cardiopulmonary symptoms -> vitals/exam/CXR/EKG ->
clinical judgment -> pretest probability).

This is an independent re-implementation, transcribed directly from the
compute() function in index.html (not imported from it), so that comparing
its output against the deployed app's actual UI output (via
run_app_validation.js) is a real check of whether the shipped JS matches
its own documented algorithm -- not a tautology.

IMPORTANT SCOPE NOTE: age and sex are generated for demographic variety and
included in patients.json, but the Wells Expanded Criteria Pathway's
pretest-probability computation (Steps 1-3) does not use either -- they
only enter the app's logic later, at the PERC step (age >= 50), which is
outside the scope of this run (see README: this validates pretest
probability only, not the full PERC/D-dimer/imaging pipeline).

Deterministic (fixed seed) so reruns are reproducible.
"""

import json
import random

SEED = 42
N_PATIENTS = 400

RESP_KEYS = ["syncope", "dyspnea", "pleuritic", "hemoptysis", "nonpleuritic"]
ASSOC_KEYS = ["ventilated", "lowFever", "legSymptoms", "pleuralRub", "jvp", "s1q3t3", "rbbb", "cxr"]
RISK_KEYS = ["surgery", "immobilization", "priorVte", "fracture", "familyHx", "cancer", "postpartum", "paralysis"]

# Per-item probability of being positive. Chosen to be well above/below the
# true clinical prevalence of each finding so that 400 random patients give
# good combinatorial coverage of every branch in compute() (severe/typical/
# atypical x asLikely/lessLikely x riskPresent/not), rather than realistic
# population-level rates that would rarely trip the rarer branches (e.g.
# syncope, jvp+ekg combos).
RESP_P = {"syncope": 0.10, "dyspnea": 0.35, "pleuritic": 0.30, "hemoptysis": 0.15, "nonpleuritic": 0.25}
ASSOC_P = {"ventilated": 0.08, "lowFever": 0.20, "legSymptoms": 0.25, "pleuralRub": 0.15,
           "jvp": 0.15, "s1q3t3": 0.12, "rbbb": 0.12, "cxr": 0.20}
RISK_P = {"surgery": 0.15, "immobilization": 0.15, "priorVte": 0.15, "fracture": 0.08,
          "familyHx": 0.10, "cancer": 0.12, "postpartum": 0.05, "paralysis": 0.06}


def gen_patient(pid, rng):
    age = rng.randint(18, 95)
    sex = rng.choice(["F", "M"])

    resp = {k: rng.random() < RESP_P[k] for k in RESP_KEYS}
    assoc = {k: rng.random() < ASSOC_P[k] for k in ASSOC_KEYS}
    risk = {k: rng.random() < RISK_P[k] for k in RISK_KEYS}

    sbp = rng.randint(70, 180)
    hr = rng.randint(50, 160)
    ra_spo2 = rng.randint(85, 100)
    # fio2Correct is only ever entered in the UI (and only ever matters to
    # compute()) when room-air SpO2 < 92; generate it only in that case,
    # matching the app's own conditional-required-field behavior.
    fio2_correct = rng.randint(21, 100) if ra_spo2 < 92 else None

    alt_dx = rng.choice(["lessLikely", "asLikely"])

    return {
        "id": pid,
        "age": age,
        "sex": sex,
        "resp": resp,
        "assoc": assoc,
        "risk": risk,
        "sbp": sbp,
        "hr": hr,
        "raSpo2": ra_spo2,
        "fio2Correct": fio2_correct,
        "altDx": alt_dx,
    }


def auto_shock(p):
    sbp = p["sbp"]
    hr = p["hr"]
    fio2_correct = p["fio2Correct"]
    vent = bool(p["assoc"]["ventilated"])
    if sbp is None:
        return False
    if sbp >= 90:
        return False
    tachy = hr is not None and hr > 100
    high_o2 = fio2_correct is not None and fio2_correct >= 40
    return bool(tachy or vent or high_o2)


RESP_POINT_KEYS = ["dyspnea", "pleuritic", "hemoptysis", "nonpleuritic", "pleuralRub", "cxr"]


def compute_reference(p):
    """Direct Python transcription of compute() in index.html."""
    resp = p["resp"]
    assoc = p["assoc"]
    risk = p["risk"]

    checked_count = sum(1 for k in RESP_POINT_KEYS if resp.get(k) or assoc.get(k))
    hypoxia = (p["raSpo2"] is not None and p["raSpo2"] < 92
               and p["fio2Correct"] is not None and p["fio2Correct"] < 40)
    resp_count = checked_count + (1 if hypoxia else 0)

    cxr = bool(resp.get("cxr") or assoc.get("cxr"))
    hr = p["hr"]
    typical_secondary = (hr is not None and hr > 90) or bool(assoc.get("legSymptoms")) or bool(assoc.get("lowFever")) or cxr
    is_typical = resp_count >= 2 and typical_secondary
    has_symptoms = resp_count >= 1 or (hr is not None and hr > 90)

    shock = auto_shock(p)
    severe_criteria = bool(resp.get("syncope")) or shock or (bool(assoc.get("jvp")) and (bool(assoc.get("s1q3t3")) or bool(assoc.get("rbbb"))))

    if severe_criteria:
        category = "severe"
    elif is_typical:
        category = "typical"
    else:
        category = "atypical"  # also the conservative fallback when !hasSymptoms, per app comment

    risk_present = any(risk.get(k) for k in RISK_KEYS)
    alt_dx = p["altDx"]

    pretest = None
    if alt_dx:
        if category == "severe":
            pretest = "high" if alt_dx == "lessLikely" else "moderate"
        elif category == "typical":
            if alt_dx == "asLikely":
                pretest = "moderate" if risk_present else "low"
            else:
                pretest = "high" if risk_present else "moderate"
        else:  # atypical
            if alt_dx == "asLikely":
                pretest = "low"
            else:
                pretest = "high" if risk_present else "moderate"

    return {
        "respCount": resp_count,
        "isTypical": is_typical,
        "hasSymptoms": has_symptoms,
        "severeCriteria": severe_criteria,
        "shock": shock,
        "category": category,
        "riskPresent": risk_present,
        "altDx": alt_dx,
        "pretest": pretest,
    }


def main():
    rng = random.Random(SEED)
    patients = [gen_patient(i + 1, rng) for i in range(N_PATIENTS)]
    for p in patients:
        p["reference"] = compute_reference(p)

    with open("patients.json", "w") as f:
        json.dump(patients, f, indent=2)

    tally = {"low": 0, "moderate": 0, "high": 0}
    for p in patients:
        tally[p["reference"]["pretest"]] += 1
    print(f"Generated {len(patients)} patients (seed={SEED}).")
    print(f"Reference pretest distribution: {tally}")
    print("Wrote patients.json")


if __name__ == "__main__":
    main()
