#!/usr/bin/env python3
"""
Generates 200 randomized synthetic adult patients -- 100 routed through the
Wells Expanded Criteria Pathway and 100 through the Clinical Gestalt Pathway
-- and scores each one, end to end, with a from-scratch Python reference
implementation of the app's documented decision rules.

This run scores the FULL pipeline: pretest probability -> PERC -> YEARS-adjusted D-dimer
threshold -> the measured D-dimer's interpretation -> the final recommended
test. The scored endpoint is the app's recommendation:

  none_perc_negative  PERC 0/8 at low probability -- no D-dimer, no imaging
  ddimer_ruled_out    measured D-dimer below its YEARS-adjusted threshold
  ddimer_imaging      measured D-dimer at or above that threshold -> CTPA
  ctpa_direct         high probability, hemodynamically stable -> CTPA
  bedside_tte         high probability with shock criteria met -> bedside TTE

This is an independent re-implementation, transcribed from compute(),
percResult(), yearsResult(), getDdimerThreshold(), renderFinal() and their
gw* counterparts in index.html (not imported from it), so comparing it
against the deployed app's actual UI output (via run_app_validation.js) is a
real check of whether the shipped JS matches its own documented algorithm --
not a tautology.

IMPORTANT SCOPE NOTE: these are synthetic patients with no real-world
diagnosis. "Accuracy" here means agreement between the live app and the
algorithm it documents -- a software-correctness check, not a claim about
diagnostic performance.

Deterministic (fixed seed) so reruns are reproducible.
"""

import json
import random

SEED = 2026
N_WELLS = 100
N_GESTALT = 100

# ---------------------------------------------------------------- Wells arm

RESP_KEYS = ["syncope", "dyspnea", "pleuritic", "hemoptysis", "nonpleuritic"]
ASSOC_KEYS = ["ventilated", "lowFever", "legSymptoms", "pleuralRub", "jvp", "s1q3t3", "rbbb", "cxr"]
RISK_KEYS = ["surgery", "immobilization", "priorVte", "fracture", "familyHx", "cancer", "postpartum", "paralysis"]
PERC_NEW_KEYS = ["estrogenUse", "recentSurgeryTrauma"]

RESP_P = {"syncope": 0.10, "dyspnea": 0.35, "pleuritic": 0.30, "hemoptysis": 0.15, "nonpleuritic": 0.25}
ASSOC_P = {"ventilated": 0.08, "lowFever": 0.20, "legSymptoms": 0.25, "pleuralRub": 0.15,
           "jvp": 0.15, "s1q3t3": 0.12, "rbbb": 0.12, "cxr": 0.20}
RISK_P = {"surgery": 0.15, "immobilization": 0.15, "priorVte": 0.15, "fracture": 0.08,
          "familyHx": 0.10, "cancer": 0.12, "postpartum": 0.05, "paralysis": 0.06}
PERC_NEW_P = {"estrogenUse": 0.12, "recentSurgeryTrauma": 0.12}

# Gestalt-arm PERC items are all asked fresh (no carry-over), so each is an
# independent input rather than derived from earlier screens.
GW_PERC_KEYS = ["hr100", "spo2Low", "hemoptysis", "legSwelling", "priorVte", "estrogenUse", "surgeryTrauma"]
# Kept low so an all-negative PERC (score 0/8, the no-testing branch) comes up
# often enough to be exercised, rather than being swamped by random positives.
GW_PERC_P = 0.12
GW_YEARS_KEYS = ["dvt", "hemoptysis", "peMostLikely"]
GW_YEARS_P = 0.35

# D-dimer values are drawn to straddle both thresholds, with the exact
# boundary values (499/500/999/1000) over-sampled so the strict "<" rule is
# exercised rather than only comfortably-clear cases.
DDIMER_BOUNDARIES = [499, 500, 501, 999, 1000, 1001]


def gen_ddimer(rng):
    if rng.random() < 0.25:
        return rng.choice(DDIMER_BOUNDARIES)
    return rng.randint(50, 2500)


def gen_wells_patient(pid, rng):
    ra_spo2 = rng.randint(85, 100)
    return {
        "id": pid,
        "pathway": "wells",
        "age": rng.randint(18, 95),
        "sex": rng.choice(["F", "M"]),
        "resp": {k: rng.random() < RESP_P[k] for k in RESP_KEYS},
        "assoc": {k: rng.random() < ASSOC_P[k] for k in ASSOC_KEYS},
        "risk": {k: rng.random() < RISK_P[k] for k in RISK_KEYS},
        "sbp": rng.randint(70, 180),
        "hr": rng.randint(50, 160),
        "raSpo2": ra_spo2,
        # Only entered in the UI (and only used by compute()) when room-air
        # SpO2 < 92, matching the app's conditional-required-field behavior.
        "fio2Correct": rng.randint(21, 100) if ra_spo2 < 92 else None,
        "altDx": rng.choice(["lessLikely", "asLikely"]),
        "percNew": {k: rng.random() < PERC_NEW_P[k] for k in PERC_NEW_KEYS},
        "ddimer": gen_ddimer(rng),
    }


def gen_gestalt_patient(pid, rng):
    return {
        "id": pid,
        "pathway": "gestalt",
        "age": rng.randint(18, 95),
        "sex": rng.choice(["F", "M"]),
        "gestaltPick": rng.choice(["low", "intermediate", "high"]),
        "gwPerc": {k: rng.random() < GW_PERC_P for k in GW_PERC_KEYS},
        "gwYears": {k: rng.random() < GW_YEARS_P for k in GW_YEARS_KEYS},
        "ddimer": gen_ddimer(rng),
        "instability": {
            "sbp": rng.randint(70, 180),
            "hr": rng.randint(50, 160),
            "fio2Correct": rng.choice([None, rng.randint(21, 100)]),
            "vent": rng.random() < 0.10,
        },
    }


# ------------------------------------------------------- reference scoring

RESP_POINT_KEYS = ["dyspnea", "pleuritic", "hemoptysis", "nonpleuritic", "pleuralRub", "cxr"]


def auto_shock(sbp, hr, fio2_correct, vent):
    """Transcription of autoShock()/gwAutoShock()."""
    if sbp is None or sbp >= 90:
        return False
    tachy = hr is not None and hr > 100
    high_o2 = fio2_correct is not None and fio2_correct >= 40
    return bool(tachy or vent or high_o2)


def wells_pretest(p):
    """Transcription of compute() in index.html."""
    resp, assoc, risk = p["resp"], p["assoc"], p["risk"]

    checked = sum(1 for k in RESP_POINT_KEYS if resp.get(k) or assoc.get(k))
    hypoxia = (p["raSpo2"] is not None and p["raSpo2"] < 92
               and p["fio2Correct"] is not None and p["fio2Correct"] < 40)
    resp_count = checked + (1 if hypoxia else 0)

    cxr = bool(resp.get("cxr") or assoc.get("cxr"))
    hr = p["hr"]
    typical_secondary = (hr is not None and hr > 90) or bool(assoc.get("legSymptoms")) \
        or bool(assoc.get("lowFever")) or cxr
    is_typical = resp_count >= 2 and typical_secondary

    shock = auto_shock(p["sbp"], hr, p["fio2Correct"], bool(assoc.get("ventilated")))
    severe = bool(resp.get("syncope")) or shock \
        or (bool(assoc.get("jvp")) and (bool(assoc.get("s1q3t3")) or bool(assoc.get("rbbb"))))

    category = "severe" if severe else ("typical" if is_typical else "atypical")
    risk_present = any(risk.get(k) for k in RISK_KEYS)
    alt_dx = p["altDx"]

    if category == "severe":
        pretest = "high" if alt_dx == "lessLikely" else "moderate"
    elif category == "typical":
        if alt_dx == "asLikely":
            pretest = "moderate" if risk_present else "low"
        else:
            pretest = "high" if risk_present else "moderate"
    else:
        if alt_dx == "asLikely":
            pretest = "low"
        else:
            pretest = "high" if risk_present else "moderate"

    return {"respCount": resp_count, "category": category, "riskPresent": risk_present,
            "shock": shock, "pretest": pretest}


def wells_perc_score(p):
    """Transcription of percResult(): 5 carried-over items + 2 fresh + age."""
    carried = [
        p["hr"] is not None and p["hr"] >= 100,
        p["raSpo2"] is not None and p["raSpo2"] < 95,
        bool(p["resp"].get("hemoptysis")),
        bool(p["assoc"].get("legSymptoms")),
        bool(p["risk"].get("priorVte")),
    ]
    fresh = [bool(p["percNew"][k]) for k in PERC_NEW_KEYS]
    age_item = p["age"] is not None and p["age"] >= 50
    return sum(carried) + sum(fresh) + (1 if age_item else 0)


def wells_years_count(p):
    """Transcription of yearsResult(): all three items carried over."""
    items = [
        bool(p["assoc"].get("legSymptoms")),          # clinical signs of DVT
        bool(p["resp"].get("hemoptysis")),            # hemoptysis
        p["altDx"] == "lessLikely",                   # PE most likely diagnosis
    ]
    return sum(items)


def gestalt_perc_score(p):
    """Transcription of gwPercResult(): 7 fresh items + age."""
    return sum(1 for k in GW_PERC_KEYS if p["gwPerc"][k]) + (1 if p["age"] >= 50 else 0)


def gestalt_years_count(p):
    return sum(1 for k in GW_YEARS_KEYS if p["gwYears"][k])


def ddimer_threshold(years_count):
    """Transcription of getDdimerThreshold()/gwGetDdimerThreshold()."""
    return 1000 if years_count == 0 else 500


def score_wells(p):
    base = wells_pretest(p)
    pretest = base["pretest"]
    out = dict(base)
    out.update({"percScore": None, "yearsCount": None, "threshold": None})

    if pretest == "high":
        out["recommendation"] = "bedside_tte" if base["shock"] else "ctpa_direct"
        return out

    if pretest == "low":
        perc = wells_perc_score(p)
        out["percScore"] = perc
        if perc == 0:
            out["recommendation"] = "none_perc_negative"
            return out

    years = wells_years_count(p)
    threshold = ddimer_threshold(years)
    out["yearsCount"] = years
    out["threshold"] = threshold
    out["recommendation"] = "ddimer_ruled_out" if p["ddimer"] < threshold else "ddimer_imaging"
    return out


def score_gestalt(p):
    pretest = p["gestaltPick"]
    inst = p["instability"]
    shock = auto_shock(inst["sbp"], inst["hr"], inst["fio2Correct"], inst["vent"])
    out = {"pretest": pretest, "shock": shock, "percScore": None,
           "yearsCount": None, "threshold": None}

    if pretest == "high":
        out["recommendation"] = "bedside_tte" if shock else "ctpa_direct"
        return out

    if pretest == "low":
        perc = gestalt_perc_score(p)
        out["percScore"] = perc
        if perc == 0:
            out["recommendation"] = "none_perc_negative"
            return out

    years = gestalt_years_count(p)
    threshold = ddimer_threshold(years)
    out["yearsCount"] = years
    out["threshold"] = threshold
    out["recommendation"] = "ddimer_ruled_out" if p["ddimer"] < threshold else "ddimer_imaging"
    return out


def main():
    rng = random.Random(SEED)
    patients = []
    for i in range(N_WELLS):
        patients.append(gen_wells_patient(i + 1, rng))
    for i in range(N_GESTALT):
        patients.append(gen_gestalt_patient(N_WELLS + i + 1, rng))

    for p in patients:
        p["reference"] = score_wells(p) if p["pathway"] == "wells" else score_gestalt(p)

    with open("patients.json", "w") as f:
        json.dump(patients, f, indent=2)

    tally = {}
    for p in patients:
        r = p["reference"]["recommendation"]
        tally[r] = tally.get(r, 0) + 1
    print(f"Generated {len(patients)} patients (seed={SEED}): "
          f"{N_WELLS} Wells Expanded, {N_GESTALT} Clinical Gestalt.")
    print("Reference recommendation distribution:")
    for k in sorted(tally):
        print(f"  {k}: {tally[k]}")
    print("Wrote patients.json")


if __name__ == "__main__":
    main()
