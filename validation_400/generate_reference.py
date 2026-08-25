#!/usr/bin/env python3
"""
Independent patient generator + reference implementation for the Acute PE
Predictor app.

This is written from scratch in a different language (Python) than the app
(JavaScript), reasoning only from the documented decision rules, NOT by
reading or copying index.html's compute()/percResult()/yearsResult()
functions line-for-line. It exists so the app can be checked against a
second, independently-authored implementation of the same specification
rather than against itself.

It also independently scores the classic published Wells criteria (Wells PS
et al. Ann Intern Med. 1998) as an external clinical benchmark, since the
app's own categorical algorithm (typical/atypical/severe + alternative-
diagnosis + risk-factor layering) is a bespoke simplification, not a
line-for-line implementation of the classic weighted Wells score.

Output: patients.json — 400 synthetic patients with random inputs, each
annotated with this reference implementation's outputs.
"""

import json
import random

N_PATIENTS = 400
SEED = 20260826  # fixed for reproducibility

RESP_KEYS = ["syncope", "dyspnea", "pleuritic", "hemoptysis", "nonpleuritic"]
ASSOC_KEYS = ["ventilated", "lowFever", "legSymptoms", "pleuralRub", "jvp", "s1q3t3", "rbbb", "cxr"]
RISK_KEYS = ["surgery", "immobilization", "priorVte", "fracture", "familyHx", "cancer", "postpartum", "paralysis"]

RESP_POINT_KEYS = ["dyspnea", "pleuritic", "hemoptysis", "nonpleuritic", "pleuralRub", "cxr"]


def gen_patient(rng, idx):
    p = {"id": idx}
    p["age"] = rng.randint(18, 95)
    p["resp"] = {k: rng.random() < 0.28 for k in RESP_KEYS}
    p["hr"] = rng.randint(40, 165)
    p["sbp"] = rng.randint(55, 200)
    p["raSpo2"] = rng.randint(75, 100)
    p["fio2Correct"] = rng.randint(21, 100)
    p["assoc"] = {k: rng.random() < 0.22 for k in ASSOC_KEYS}
    p["risk"] = {k: rng.random() < 0.18 for k in RISK_KEYS}
    p["altDx"] = rng.choice(["lessLikely", "asLikely"])
    p["estrogenUse"] = rng.random() < 0.15
    p["recentSurgeryTrauma"] = rng.random() < 0.15
    p["ddimer"] = rng.randint(50, 3000)
    return p


def auto_shock(p):
    sbp = p["sbp"]
    if sbp is None or sbp >= 90:
        return False
    tachy = p["hr"] is not None and p["hr"] > 100
    high_o2 = p["fio2Correct"] is not None and p["fio2Correct"] >= 40
    vent = bool(p["assoc"]["ventilated"])
    return bool(tachy or vent or high_o2)


def reference_pretest(p):
    """Independent re-derivation of the app's documented categorization
    rule: respiratory-point count -> typical/atypical/severe category,
    then layered with alternative-diagnosis judgment and VTE risk factors."""
    checked = sum(1 for k in RESP_POINT_KEYS if p["resp"].get(k) or p["assoc"].get(k))
    hypoxia = p["raSpo2"] is not None and p["raSpo2"] < 92 and p["fio2Correct"] is not None and p["fio2Correct"] < 40
    resp_count = checked + (1 if hypoxia else 0)
    cxr = bool(p["assoc"]["cxr"])
    typical_secondary = (p["hr"] is not None and p["hr"] > 90) or bool(p["assoc"]["legSymptoms"]) or bool(p["assoc"]["lowFever"]) or cxr
    is_typical = resp_count >= 2 and typical_secondary

    shock = auto_shock(p)
    severe = bool(p["resp"]["syncope"]) or shock or (bool(p["assoc"]["jvp"]) and (bool(p["assoc"]["s1q3t3"]) or bool(p["assoc"]["rbbb"])))

    if severe:
        category = "severe"
    elif is_typical:
        category = "typical"
    else:
        category = "atypical"

    risk_present = any(p["risk"].values())
    alt_dx = p["altDx"]

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
        "category": category,
        "severeCriteria": severe,
        "isTypical": is_typical,
        "riskPresent": risk_present,
        "pretest": pretest,
    }


def reference_perc(p):
    """Independent re-derivation of the 8-item PERC rule (age, HR, SpO2,
    hemoptysis, unilateral leg swelling, prior DVT/PE, estrogen use, recent
    surgery/trauma). Only meaningful when pretest probability is Low."""
    items = {
        "age50": p["age"] >= 50,
        "hr100": p["hr"] is not None and p["hr"] >= 100,
        "spo2": p["raSpo2"] is not None and p["raSpo2"] < 95,
        "hemoptysis": bool(p["resp"]["hemoptysis"]),
        "legSwelling": bool(p["assoc"]["legSymptoms"]),
        "priorVte": bool(p["risk"]["priorVte"]),
        "estrogenUse": bool(p["estrogenUse"]),
        "recentSurgeryTrauma": bool(p["recentSurgeryTrauma"]),
    }
    score = sum(1 for v in items.values() if v)
    return {"items": items, "score": score, "negative": score == 0}


def reference_years(p):
    """Independent re-derivation of the 3-item YEARS rule (signs of DVT,
    hemoptysis, PE the most likely diagnosis). Only meaningful when pretest
    probability is Moderate."""
    items = {
        "dvt": bool(p["assoc"]["legSymptoms"]),
        "hemoptysis": bool(p["resp"]["hemoptysis"]),
        "peMostLikely": p["altDx"] == "lessLikely",
    }
    count = sum(1 for v in items.values() if v)
    threshold = 1000 if count == 0 else 500
    return {"items": items, "itemCount": count, "threshold": threshold}


def classic_wells_score(p):
    """The published 7-item weighted Wells score (Wells PS, Ginsberg JS,
    Anderson DR, et al. Ann Intern Med. 1998;129(12):997-1005), used here
    purely as an external clinical benchmark — the app does not implement
    this scoring system directly, so this checks how often the app's
    bespoke categorization agrees with the traditional weighted score on
    the same inputs."""
    pts = 0.0
    if p["assoc"]["legSymptoms"]:
        pts += 3.0
    if p["altDx"] == "lessLikely":  # PE is the most likely diagnosis
        pts += 3.0
    if p["hr"] is not None and p["hr"] > 100:
        pts += 1.5
    if p["risk"]["immobilization"] or p["risk"]["surgery"]:
        pts += 1.5
    if p["risk"]["priorVte"]:
        pts += 1.5
    if p["resp"]["hemoptysis"]:
        pts += 1.0
    if p["risk"]["cancer"]:
        pts += 1.0
    if pts < 2:
        tier = "low"
    elif pts <= 6:
        tier = "moderate"
    else:
        tier = "high"
    return {"points": pts, "tier": tier}


def main():
    rng = random.Random(SEED)
    patients = []
    for i in range(1, N_PATIENTS + 1):
        p = gen_patient(rng, i)
        p["reference"] = {
            "pretest": reference_pretest(p),
            "perc": reference_perc(p),
            "years": reference_years(p),
            "classicWells": classic_wells_score(p),
        }
        patients.append(p)

    with open("patients.json", "w") as f:
        json.dump(patients, f, indent=1)

    tiers = {}
    for p in patients:
        t = p["reference"]["pretest"]["pretest"]
        tiers[t] = tiers.get(t, 0) + 1
    print(f"Generated {len(patients)} patients (seed={SEED})")
    print("Reference pretest-probability distribution:", tiers)


if __name__ == "__main__":
    main()
