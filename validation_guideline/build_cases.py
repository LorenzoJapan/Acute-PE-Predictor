#!/usr/bin/env python3
"""
Builds cases.json: 100 guideline-anchored golden cases for the Acute PE
Predictor.

HOW THIS DIFFERS FROM validation_200/
-------------------------------------
That suite compares the app against a Python transcription of the app's own
code. It can only detect divergence between the shipped JavaScript and its
documented algorithm; if the algorithm itself is wrong, both sides agree and
the bug passes.

Here, every expected answer is written by hand from the primary literature and
the 2026 AHA/ACC PE guideline's diagnostic algorithm -- NOT derived from
index.html. Each case carries the citation that dictates its answer. These
cases can therefore fail in a way the other suites cannot: they can say the
app is clinically wrong rather than merely self-inconsistent.

WHAT EACH CASE CAN AND CANNOT ANCHOR
------------------------------------
Clinical Gestalt Pathway cases stipulate the pretest probability tier as a
direct input (the clinician picks it), so everything downstream -- PERC, the
YEARS-adjusted D-dimer threshold, the interpretation of the measured value,
and the imaging decision -- is fully anchored to published rules.

Wells Expanded Criteria Pathway cases also exercise the app's own three-step
expansion of the Wells elements into a pretest tier. That expansion is the
app's own construct and has no external authority, so for those cases the
tier is recorded as `tier_is_app_construct: true`: the guideline-anchored
assertion is the pipeline downstream of the tier (PERC carry-over, YEARS
carry-over, threshold, recommendation), not the tier derivation itself.

BINDING vs ADVISORY
-------------------
`advisory: true` cases test behavior where the cited authorities disagree, or
where the guideline endorses an option the app documents that it does not
implement. They are reported separately and excluded from the headline
accuracy, because failing them is a design decision to discuss, not a defect.

Run with: python3 build_cases.py
"""

import json

# --------------------------------------------------------------- citations

SRC_PERC = ("Kline JA et al. J Thromb Haemost 2004;2(8):1247-1255 (PERC derivation); "
            "Freund Y et al. JAMA 2018;319(6):559-566 (PROPER) — PERC applies at "
            "low (<15%) pretest probability; all 8 criteria negative excludes PE "
            "without further testing.")
SRC_YEARS = ("van der Hulle T et al. Lancet 2017;390(10091):289-297 (YEARS) — 0 YEARS "
             "items: D-dimer <1000 ng/mL FEU excludes PE; >=1 item: <500 ng/mL FEU.")
SRC_PEGED = ("Kearon C et al. N Engl J Med 2019;381(22):2125-2134 (PEGeD) — D-dimer "
             "interpreted against a clinical-probability-adjusted threshold.")
SRC_GDL_YEARS = ("2026 AHA/ACC/ACCP/ACEP/CHEST/SCAI/SHM/SIR/SVM/SVN PE guideline "
                 "(Circulation 2026;153) — YEARS-adjusted D-dimer endorsed for low or "
                 "intermediate (<50%) pretest probability, Class 2a LOE B-R.")
SRC_GDL_IMG = ("2026 AHA/ACC PE guideline — imaging is recommended for patients deemed "
               "high probability (>50%) or with an elevated D-dimer (Class 1, LOE A); "
               "CTPA is recommended in preference to V/Q scanning (Class 1, LOE B-R).")
SRC_GDL_PERC = ("2026 AHA/ACC PE guideline diagnostic algorithm — at low clinical "
                "probability apply PERC; if PERC cannot exclude PE, the patient moves "
                "into the same D-dimer + YEARS assessment as intermediate probability.")
SRC_ESC = ("Konstantinides SV et al. Eur Heart J 2020;41(4):543-603 (2019 ESC) — in "
           "suspected high-risk PE with haemodynamic instability, bedside "
           "echocardiography is used when CTPA is not immediately available.")
SRC_GDL_ECHO = ("2026 AHA/ACC PE guideline — an echocardiogram is NOT recommended to "
                "confirm or refute the diagnosis of PE (Class 3: No Benefit, LOE B-NR); "
                "echocardiography is for risk stratification once PE is confirmed. This "
                "conflicts with the 2019 ESC position the app cites for this branch.")
SRC_GDL_AGEADJ = ("2026 AHA/ACC PE guideline — an age-adjusted D-dimer threshold "
                  "(age x 10 ug/L FEU in patients >50) is a reasonable alternative at "
                  "low or intermediate probability (Class 2a, LOE B-R). The app "
                  "implements YEARS adjustment only, not age adjustment.")

# Recommendation vocabulary (same five endpoints validation_200 scores).
NONE_PERC = "none_perc_negative"
RULED_OUT = "ddimer_ruled_out"
DD_IMAGING = "ddimer_imaging"
CTPA = "ctpa_direct"
TTE = "bedside_tte"

GW_PERC_KEYS = ["hr100", "spo2Low", "hemoptysis", "legSwelling", "priorVte", "estrogenUse", "surgeryTrauma"]
GW_YEARS_KEYS = ["dvt", "hemoptysis", "peMostLikely"]
RESP_KEYS = ["syncope", "dyspnea", "pleuritic", "hemoptysis", "nonpleuritic"]
ASSOC_KEYS = ["ventilated", "lowFever", "legSymptoms", "pleuralRub", "jvp", "s1q3t3", "rbbb", "cxr"]
RISK_KEYS = ["surgery", "immobilization", "priorVte", "fracture", "familyHx", "cancer", "postpartum", "paralysis"]
PERC_NEW_KEYS = ["estrogenUse", "recentSurgeryTrauma"]

CASES = []


def gestalt(vignette, tier, expect, source, rule, age=40, perc=(), years=(),
            ddimer=None, threshold=None, sbp=120, hr=80, fio2=None, vent=False,
            advisory=False, note=None):
    """A Clinical Gestalt Pathway case. `tier` is a stipulated input, so the
    whole downstream pipeline is guideline-anchored."""
    CASES.append({
        "id": len(CASES) + 1,
        "pathway": "gestalt",
        "vignette": vignette,
        "age": age,
        "gestaltPick": tier,
        "gwPerc": {k: (k in perc) for k in GW_PERC_KEYS},
        "gwYears": {k: (k in years) for k in GW_YEARS_KEYS},
        "ddimer": ddimer,
        "instability": {"sbp": sbp, "hr": hr, "fio2Correct": fio2, "vent": vent},
        "expected": {"recommendation": expect, "threshold": threshold},
        "rule": rule,
        "source": source,
        "advisory": advisory,
        "note": note,
        "tier_is_app_construct": False,
    })


def wells(vignette, expect, source, rule, age=40, resp=(), assoc=(), risk=(),
          sbp=120, hr=80, raSpo2=98, fio2=None, altDx="asLikely", perc_new=(),
          ddimer=None, threshold=None, expected_tier=None, advisory=False, note=None):
    """A Wells Expanded Criteria Pathway case. The tier derivation is the app's
    own construct (see module docstring); the guideline-anchored assertion is
    the recommendation the pipeline reaches from that tier."""
    CASES.append({
        "id": len(CASES) + 1,
        "pathway": "wells",
        "vignette": vignette,
        "age": age,
        "resp": {k: (k in resp) for k in RESP_KEYS},
        "assoc": {k: (k in assoc) for k in ASSOC_KEYS},
        "risk": {k: (k in risk) for k in RISK_KEYS},
        "sbp": sbp, "hr": hr, "raSpo2": raSpo2, "fio2Correct": fio2,
        "altDx": altDx,
        "percNew": {k: (k in perc_new) for k in PERC_NEW_KEYS},
        "ddimer": ddimer,
        "expected": {"recommendation": expect, "threshold": threshold},
        "expected_tier": expected_tier,
        "rule": rule,
        "source": source,
        "advisory": advisory,
        "note": note,
        "tier_is_app_construct": True,
    })


# =====================================================================
# BLOCK A — PERC negative at low probability excludes PE with no testing
# =====================================================================
gestalt("32F, pleuritic chest pain after a long desk day; no risk factors, vitals normal. Gestalt low.",
        "low", NONE_PERC, SRC_PERC, "PERC 0/8 at low probability -> no D-dimer, no imaging", age=32)
gestalt("22M, anxiety-related dyspnea, entirely normal exam and vitals. Gestalt low.",
        "low", NONE_PERC, SRC_PERC, "PERC 0/8 -> PE excluded", age=22)
gestalt("49F, atypical chest pain, HR 88, SpO2 98%, no hormones, no prior VTE. Gestalt low.",
        "low", NONE_PERC, SRC_PERC, "Age 49 is below the PERC age cut-off of 50", age=49)
gestalt("18M, chest wall pain after weightlifting. Gestalt low.",
        "low", NONE_PERC, SRC_PERC, "PERC 0/8 at the youngest adult age", age=18)
gestalt("45M, cough and mild dyspnea, no PERC criteria met. Gestalt low.",
        "low", NONE_PERC, SRC_PERC, "PERC 0/8 -> no further testing", age=45)
gestalt("38F, costochondritis, normal vitals, no estrogen. Gestalt low.",
        "low", NONE_PERC, SRC_PERC, "PERC 0/8 -> no further testing", age=38)
wells("41M, isolated atypical chest discomfort; alternative diagnosis as likely as PE.",
      NONE_PERC, SRC_PERC, "Low tier -> PERC 0/8 -> no testing", age=41, expected_tier="low")
wells("29F, pleuritic pain only; normal vitals; alternative diagnosis as likely as PE.",
      NONE_PERC, SRC_PERC, "Low tier -> PERC 0/8 -> no testing", age=29,
      resp=("pleuritic",), expected_tier="low")

# =====================================================================
# BLOCK B — Each single PERC criterion must block PERC exclusion
# One case per criterion: the ONLY positive finding is that criterion,
# so an app that drops it would wrongly report "PE excluded".
# =====================================================================
gestalt("58F, otherwise unremarkable; age >=50 is the only PERC criterion met. Gestalt low.",
        "low", RULED_OUT, SRC_GDL_PERC, "PERC age criterion alone -> PERC positive -> D-dimer (YEARS 0 -> <1000)",
        age=58, ddimer=400, threshold=1000)
gestalt("34M, HR 104; no other PERC criterion. Gestalt low.",
        "low", RULED_OUT, SRC_PERC, "PERC tachycardia criterion alone -> D-dimer path",
        age=34, perc=("hr100",), ddimer=400, threshold=1000)
gestalt("36F, room-air SpO2 93%; no other PERC criterion. Gestalt low.",
        "low", RULED_OUT, SRC_PERC, "PERC hypoxia criterion alone -> D-dimer path",
        age=36, perc=("spo2Low",), ddimer=400, threshold=1000)
gestalt("30M, hemoptysis; no other PERC criterion. Gestalt low.",
        "low", DD_IMAGING, SRC_YEARS, "Hemoptysis is both a PERC criterion and a YEARS item -> threshold 500",
        age=30, perc=("hemoptysis",), years=("hemoptysis",), ddimer=600, threshold=500)
gestalt("28F, unilateral calf swelling; no other PERC criterion. Gestalt low.",
        "low", DD_IMAGING, SRC_YEARS, "Leg swelling is a PERC criterion and the YEARS DVT item -> threshold 500",
        age=28, perc=("legSwelling",), years=("dvt",), ddimer=600, threshold=500)
gestalt("33F, prior DVT; no other PERC criterion. Gestalt low.",
        "low", RULED_OUT, SRC_PERC, "PERC prior-VTE criterion alone -> D-dimer path",
        age=33, perc=("priorVte",), ddimer=900, threshold=1000)
gestalt("26F, combined oral contraceptive use; no other PERC criterion. Gestalt low.",
        "low", RULED_OUT, SRC_PERC, "PERC estrogen criterion alone -> D-dimer path",
        age=26, perc=("estrogenUse",), ddimer=900, threshold=1000)
gestalt("40M, knee arthroscopy under general anaesthesia 2 weeks ago; no other PERC criterion. Gestalt low.",
        "low", RULED_OUT, SRC_PERC, "PERC recent-surgery criterion alone -> D-dimer path",
        age=40, perc=("surgeryTrauma",), ddimer=900, threshold=1000)
# Wells-pathway carry-over: the same criteria captured in Steps 1-3 must reach PERC.
wells("62M, low-probability presentation; age 62 is the only PERC criterion.",
      RULED_OUT, SRC_PERC, "Age carried into PERC -> D-dimer, YEARS 0 -> <1000",
      age=62, ddimer=400, threshold=1000, expected_tier="low")
wells("35M, HR 108 carried from Step 2 vitals; otherwise low probability.",
      RULED_OUT, SRC_PERC, "HR >=100 carried into PERC -> D-dimer path",
      age=35, hr=108, ddimer=400, threshold=1000, expected_tier="low")
wells("44F, room-air SpO2 93% carried from Step 2; otherwise low probability.",
      RULED_OUT, SRC_PERC, "SpO2 <95% carried into PERC -> D-dimer path",
      age=44, raSpo2=93, ddimer=400, threshold=1000, expected_tier="low")
wells("31M, hemoptysis recorded in Step 1; otherwise low probability.",
      DD_IMAGING, SRC_YEARS, "Hemoptysis carried into both PERC and YEARS -> threshold 500",
      age=31, resp=("hemoptysis",), ddimer=600, threshold=500, expected_tier="low")
wells("37F, unilateral leg swelling recorded in Step 2; otherwise low probability.",
      DD_IMAGING, SRC_YEARS, "Signs of DVT carried into both PERC and YEARS -> threshold 500",
      age=37, assoc=("legSymptoms",), ddimer=600, threshold=500, expected_tier="low")

# =====================================================================
# BLOCK C — YEARS threshold selection (0 items -> 1000, >=1 item -> 500)
# =====================================================================
gestalt("54M, intermediate probability, no YEARS items.", "intermediate", RULED_OUT, SRC_YEARS,
        "0 YEARS items -> threshold 1000", age=54, ddimer=900, threshold=1000)
gestalt("54M, intermediate probability, signs of DVT only.", "intermediate", DD_IMAGING, SRC_YEARS,
        "1 YEARS item (DVT) -> threshold 500", age=54, years=("dvt",), ddimer=900, threshold=500)
gestalt("47F, intermediate probability, hemoptysis only.", "intermediate", DD_IMAGING, SRC_YEARS,
        "1 YEARS item (hemoptysis) -> threshold 500", age=47, years=("hemoptysis",), ddimer=900, threshold=500)
gestalt("61M, intermediate probability, PE judged the most likely diagnosis.", "intermediate", DD_IMAGING,
        SRC_YEARS, "1 YEARS item (PE most likely) -> threshold 500", age=61,
        years=("peMostLikely",), ddimer=900, threshold=500)
gestalt("59F, intermediate probability, DVT signs + hemoptysis.", "intermediate", DD_IMAGING, SRC_YEARS,
        "2 YEARS items -> threshold 500", age=59, years=("dvt", "hemoptysis"), ddimer=700, threshold=500)
gestalt("66M, intermediate probability, all three YEARS items.", "intermediate", DD_IMAGING, SRC_YEARS,
        "3 YEARS items -> threshold 500", age=66, years=("dvt", "hemoptysis", "peMostLikely"),
        ddimer=520, threshold=500)
gestalt("52F, low probability, PERC positive on age, no YEARS items.", "low", RULED_OUT, SRC_GDL_YEARS,
        "PERC-positive low probability uses the same YEARS-adjusted threshold as intermediate",
        age=52, ddimer=800, threshold=1000)
gestalt("53M, low probability, PERC positive on age, PE most likely diagnosis.", "low", DD_IMAGING,
        SRC_GDL_YEARS, "PERC-positive low probability with 1 YEARS item -> threshold 500",
        age=53, years=("peMostLikely",), ddimer=800, threshold=500)
wells("50F, moderate-tier presentation with no YEARS items and an alternative diagnosis as likely.",
      RULED_OUT, SRC_YEARS, "0 YEARS items -> threshold 1000", age=50,
      resp=("dyspnea", "pleuritic"), hr=95, risk=("cancer",), ddimer=900, threshold=1000,
      expected_tier="moderate")
wells("55M, moderate tier; clinician judges PE the most likely diagnosis (a YEARS item).",
      DD_IMAGING, SRC_YEARS, "altDx 'less likely than PE' is the YEARS 'PE most likely' item -> 500",
      age=55, altDx="lessLikely", ddimer=900, threshold=500, expected_tier="moderate")
wells("48F, moderate tier with hemoptysis carried from Step 1.", DD_IMAGING, SRC_YEARS,
      "Hemoptysis carried into YEARS -> threshold 500", age=48,
      resp=("hemoptysis", "dyspnea"), hr=95, risk=("immobilization",), ddimer=900, threshold=500,
      expected_tier="moderate")
wells("57M, moderate tier with leg swelling carried from Step 2.", DD_IMAGING, SRC_YEARS,
      "Signs of DVT carried into YEARS -> threshold 500", age=57,
      resp=("dyspnea", "pleuritic"), assoc=("legSymptoms",), risk=("cancer",), ddimer=900, threshold=500,
      expected_tier="moderate")

# =====================================================================
# BLOCK D — D-dimer boundary behavior. The rule is strictly "below the
# threshold excludes"; a value exactly at the threshold does not.
# =====================================================================
for val, exp, note in [(999, RULED_OUT, "just below 1000"), (1000, DD_IMAGING, "exactly at 1000"),
                       (1001, DD_IMAGING, "just above 1000")]:
    gestalt(f"60M, intermediate probability, no YEARS items, D-dimer {val} ng/mL FEU.",
            "intermediate", exp, SRC_YEARS, f"0 YEARS items, threshold 1000 — {note}",
            age=60, ddimer=val, threshold=1000)
for val, exp, note in [(499, RULED_OUT, "just below 500"), (500, DD_IMAGING, "exactly at 500"),
                       (501, DD_IMAGING, "just above 500")]:
    gestalt(f"60M, intermediate probability, PE most likely diagnosis, D-dimer {val} ng/mL FEU.",
            "intermediate", exp, SRC_YEARS, f"1 YEARS item, threshold 500 — {note}",
            age=60, years=("peMostLikely",), ddimer=val, threshold=500)
gestalt("62F, intermediate probability, no YEARS items, D-dimer 501 — below 1000, so excluded.",
        "intermediate", RULED_OUT, SRC_YEARS,
        "With 0 YEARS items the 500 threshold does not apply; 501 < 1000 excludes PE",
        age=62, ddimer=501, threshold=1000)
gestalt("62F, intermediate probability, DVT signs, D-dimer 999 — at/above 500, so imaging.",
        "intermediate", DD_IMAGING, SRC_YEARS,
        "With 1 YEARS item the threshold is 500; 999 >= 500 requires imaging",
        age=62, years=("dvt",), ddimer=999, threshold=500)
gestalt("44M, intermediate probability, D-dimer 50 (very low), no YEARS items.",
        "intermediate", RULED_OUT, SRC_YEARS, "Well below threshold -> excluded",
        age=44, ddimer=50, threshold=1000)
gestalt("44M, intermediate probability, D-dimer 4800 (markedly elevated).",
        "intermediate", DD_IMAGING, SRC_GDL_IMG, "Elevated D-dimer -> imaging (Class 1)",
        age=44, ddimer=4800, threshold=1000)
gestalt("51F, low probability, PERC positive on age, D-dimer exactly 1000, no YEARS items.",
        "low", DD_IMAGING, SRC_YEARS, "Exactly at threshold is not below it -> imaging",
        age=51, ddimer=1000, threshold=1000)
gestalt("51F, low probability, PERC positive on estrogen, D-dimer 999, no YEARS items.",
        "low", RULED_OUT, SRC_YEARS, "999 < 1000 -> PE excluded without imaging",
        age=40, perc=("estrogenUse",), ddimer=999, threshold=1000)
wells("63M, moderate tier, no YEARS items, D-dimer exactly 1000.", DD_IMAGING, SRC_YEARS,
      "Exactly at threshold -> imaging", age=63, resp=("dyspnea", "pleuritic"), hr=95,
      risk=("cancer",), ddimer=1000, threshold=1000, expected_tier="moderate")
wells("63M, moderate tier, no YEARS items, D-dimer 999.", RULED_OUT, SRC_YEARS,
      "999 < 1000 -> excluded", age=63, resp=("dyspnea", "pleuritic"), hr=95,
      risk=("cancer",), ddimer=999, threshold=1000, expected_tier="moderate")
wells("46F, moderate tier, PE most likely (YEARS item), D-dimer exactly 500.", DD_IMAGING, SRC_YEARS,
      "Exactly at the 500 threshold -> imaging", age=46, altDx="lessLikely",
      ddimer=500, threshold=500, expected_tier="moderate")
wells("46F, moderate tier, PE most likely (YEARS item), D-dimer 499.", RULED_OUT, SRC_YEARS,
      "499 < 500 -> excluded", age=46, altDx="lessLikely", ddimer=499, threshold=500,
      expected_tier="moderate")

# =====================================================================
# BLOCK E — High pretest probability: imaging directly, no D-dimer
# =====================================================================
gestalt("70M, sudden dyspnea and pleuritic pain with active malignancy; clinician's gestalt is high. Stable.",
        "high", CTPA, SRC_GDL_IMG, "High probability -> CTPA; D-dimer not indicated", age=70)
gestalt("64F, post-operative day 3 with tachycardia and hypoxemia; gestalt high. Stable, HR 96.",
        "high", CTPA, SRC_GDL_IMG, "High probability -> CTPA", age=64, hr=96)
gestalt("58M, prior PE off anticoagulation, now dyspneic; gestalt high. SBP 128.",
        "high", CTPA, SRC_GDL_IMG, "High probability -> CTPA", age=58, sbp=128, hr=92)
gestalt("75F, high gestalt probability, SBP 96 — hypotensive but not meeting shock criteria.",
        "high", CTPA, SRC_GDL_IMG, "SBP >=90 is not shock -> stable pathway -> CTPA",
        age=75, sbp=96, hr=104)
wells("68M, syncope with an alternative diagnosis less likely than PE.", CTPA, SRC_GDL_IMG,
      "Severe presentation, PE most likely -> high tier -> CTPA directly", age=68,
      resp=("syncope",), altDx="lessLikely", expected_tier="high")
wells("72F, raised JVP with S1Q3T3 on EKG; alternative diagnosis less likely.", CTPA, SRC_GDL_IMG,
      "Right-heart strain pattern -> severe -> high tier -> CTPA", age=72,
      assoc=("jvp", "s1q3t3"), altDx="lessLikely", expected_tier="high")
wells("66M, raised JVP with new RBBB; alternative diagnosis less likely.", CTPA, SRC_GDL_IMG,
      "Right-heart strain pattern -> severe -> high tier -> CTPA", age=66,
      assoc=("jvp", "rbbb"), altDx="lessLikely", expected_tier="high")
wells("59F, atypical presentation, alternative diagnosis less likely, active cancer.", CTPA, SRC_GDL_IMG,
      "High tier -> CTPA, no D-dimer", age=59, altDx="lessLikely", risk=("cancer",),
      expected_tier="high")

# =====================================================================
# BLOCK F — Haemodynamically unstable, high probability  [ADVISORY]
# The app offers bedside TTE per 2019 ESC when the patient cannot be
# transported. The 2026 AHA/ACC guideline gives echo a Class 3 (No
# Benefit) for confirming or refuting PE. Cited authorities conflict;
# these cases record the app's ESC-aligned behavior and flag it.
# =====================================================================
_tte_note = ("Cited authorities conflict: 2019 ESC supports bedside echocardiography in the "
             "unstable patient when CTPA is not immediately available, while the 2026 AHA/ACC "
             "guideline assigns echocardiography Class 3 (No Benefit) for confirming or refuting "
             "PE. The app follows ESC and says CTPA remains the study of choice. Reviewed as a "
             "design decision, not scored as a defect.")
gestalt("69M, high gestalt probability, SBP 78 with HR 124 — shock criteria met.",
        "high", TTE, SRC_ESC, "SBP <90 with tachycardia -> unstable branch", age=69,
        sbp=78, hr=124, advisory=True, note=_tte_note)
gestalt("74F, high probability, SBP 84, mechanically ventilated.", "high", TTE, SRC_ESC,
        "SBP <90 with mechanical ventilation -> unstable branch", age=74,
        sbp=84, hr=88, vent=True, advisory=True, note=_tte_note)
gestalt("61M, high probability, SBP 86 on FiO2 60% to maintain saturation.", "high", TTE, SRC_ESC,
        "SBP <90 with high oxygen requirement -> unstable branch", age=61,
        sbp=86, hr=90, fio2=60, advisory=True, note=_tte_note)
gestalt("57F, high probability, SBP 88 but HR 84, not ventilated, FiO2 30%.", "high", CTPA, SRC_GDL_IMG,
        "Hypotension alone without tachycardia, ventilation or high FiO2 does not meet the "
        "app's shock definition -> stable -> CTPA", age=57, sbp=88, hr=84, fio2=30,
        advisory=True, note=("The app requires SBP <90 PLUS one of tachycardia / ventilation / "
                             "FiO2 >=40%. Isolated hypotension is treated as stable. Worth "
                             "reviewing against local practice."))
wells("71M, syncope with SBP 82 and HR 118; alternative diagnosis less likely.", TTE, SRC_ESC,
      "Shock criteria met on the Wells pathway -> unstable branch", age=71,
      resp=("syncope",), sbp=82, hr=118, altDx="lessLikely", expected_tier="high",
      advisory=True, note=_tte_note)
wells("64F, high tier, SBP 85, HR 112, alternative diagnosis less likely.", TTE, SRC_ESC,
      "Shock criteria met -> unstable branch", age=64, sbp=85, hr=112,
      altDx="lessLikely", risk=("cancer",), expected_tier="high",
      advisory=True, note=_tte_note)

# =====================================================================
# BLOCK G — Intermediate-tier pipeline, varied clinical presentations
# =====================================================================
gestalt("55F, dyspnea 3 days after a transatlantic flight; gestalt intermediate, D-dimer 320.",
        "intermediate", RULED_OUT, SRC_PEGED, "0 YEARS items, 320 < 1000 -> excluded",
        age=55, ddimer=320, threshold=1000)
gestalt("43M, pleuritic pain and mild tachycardia; gestalt intermediate, D-dimer 1450.",
        "intermediate", DD_IMAGING, SRC_GDL_IMG, "0 YEARS items, 1450 >= 1000 -> CTPA",
        age=43, ddimer=1450, threshold=1000)
gestalt("67F, immobilised after hip fracture; gestalt intermediate with DVT signs, D-dimer 420.",
        "intermediate", RULED_OUT, SRC_YEARS, "1 YEARS item, 420 < 500 -> excluded",
        age=67, years=("dvt",), ddimer=420, threshold=500)
gestalt("39F, post-partum dyspnea; gestalt intermediate, no YEARS items, D-dimer 780.",
        "intermediate", RULED_OUT, SRC_YEARS, "0 YEARS items, 780 < 1000 -> excluded",
        age=39, ddimer=780, threshold=1000)
gestalt("50M, active chemotherapy, dyspnea; gestalt intermediate, PE most likely, D-dimer 620.",
        "intermediate", DD_IMAGING, SRC_YEARS, "1 YEARS item, 620 >= 500 -> CTPA",
        age=50, years=("peMostLikely",), ddimer=620, threshold=500)
gestalt("48F, calf tenderness and dyspnea; gestalt intermediate, DVT signs, D-dimer 480.",
        "intermediate", RULED_OUT, SRC_YEARS, "1 YEARS item, 480 < 500 -> excluded",
        age=48, years=("dvt",), ddimer=480, threshold=500)
gestalt("35M, pleuritic pain with hemoptysis; gestalt intermediate, D-dimer 3200.",
        "intermediate", DD_IMAGING, SRC_GDL_IMG, "1 YEARS item, markedly elevated -> CTPA",
        age=35, years=("hemoptysis",), ddimer=3200, threshold=500)
gestalt("72M, COPD exacerbation vs PE; gestalt intermediate, no YEARS items, D-dimer 960.",
        "intermediate", RULED_OUT, SRC_YEARS, "0 YEARS items, 960 < 1000 -> excluded",
        age=72, ddimer=960, threshold=1000)
gestalt("29F, oral contraceptive use, pleuritic pain; gestalt intermediate, D-dimer 1100.",
        "intermediate", DD_IMAGING, SRC_GDL_IMG, "0 YEARS items, 1100 >= 1000 -> CTPA",
        age=29, ddimer=1100, threshold=1000)
gestalt("81F, syncope and dyspnea; gestalt intermediate, PE most likely, D-dimer 450.",
        "intermediate", RULED_OUT, SRC_YEARS, "1 YEARS item, 450 < 500 -> excluded",
        age=81, years=("peMostLikely",), ddimer=450, threshold=500)
gestalt("24M, chest pain after a bar fight; gestalt intermediate, no YEARS items, D-dimer 200.",
        "intermediate", RULED_OUT, SRC_YEARS, "0 YEARS items, 200 < 1000 -> excluded",
        age=24, ddimer=200, threshold=1000)
gestalt("77M, dyspnea with leg swelling and hemoptysis; gestalt intermediate, D-dimer 505.",
        "intermediate", DD_IMAGING, SRC_YEARS, "2 YEARS items, 505 >= 500 -> CTPA",
        age=77, years=("dvt", "hemoptysis"), ddimer=505, threshold=500)

# =====================================================================
# BLOCK H — Wells-pathway pipeline, carry-over and tier combinations
# =====================================================================
wells("42M, dyspnea and pleuritic pain with HR 96; no risk factors; alternative dx as likely.",
      RULED_OUT, SRC_YEARS, "Typical presentation, no risk -> low tier -> PERC path",
      age=42, resp=("dyspnea", "pleuritic"), hr=96, perc_new=("estrogenUse",),
      ddimer=700, threshold=1000, expected_tier="low")
wells("53F, dyspnea, pleuritic pain, HR 94, recent immobilisation; alternative dx as likely.",
      RULED_OUT, SRC_YEARS, "Typical + risk -> moderate tier -> YEARS 0 -> <1000",
      age=53, resp=("dyspnea", "pleuritic"), hr=94, risk=("immobilization",),
      ddimer=850, threshold=1000, expected_tier="moderate")
wells("60M, atypical presentation, alternative dx less likely, no risk factors.",
      DD_IMAGING, SRC_YEARS, "Moderate tier; altDx 'less likely' is a YEARS item -> 500",
      age=60, altDx="lessLikely", ddimer=700, threshold=500, expected_tier="moderate")
wells("33F, pleural rub and abnormal CXR, HR 92; alternative dx as likely; no risk.",
      RULED_OUT, SRC_YEARS, "Typical tier, YEARS 0 -> <1000", age=33,
      assoc=("pleuralRub", "cxr"), hr=92, perc_new=("estrogenUse",), ddimer=650, threshold=1000,
      expected_tier="low")
wells("47M, room-air SpO2 90% corrected with FiO2 30%; dyspnea; alternative dx as likely; no risk.",
      RULED_OUT, SRC_YEARS, "Hypoxia point counted; low tier -> PERC positive on SpO2 -> D-dimer",
      age=47, resp=("dyspnea",), raSpo2=90, fio2=30, ddimer=700, threshold=1000,
      expected_tier="low")
wells("55F, dyspnea with low-grade fever, HR 98, prior VTE; alternative dx as likely.",
      DD_IMAGING, SRC_PERC, "Prior VTE carried into PERC; moderate tier -> D-dimer",
      age=55, resp=("dyspnea", "nonpleuritic"), assoc=("lowFever",), hr=98, risk=("priorVte",),
      ddimer=1200, threshold=1000, expected_tier="moderate")
wells("38M, hemoptysis and dyspnea, HR 92, no risk; alternative dx as likely.",
      DD_IMAGING, SRC_YEARS, "Hemoptysis -> YEARS 1 -> threshold 500", age=38,
      resp=("hemoptysis", "dyspnea"), hr=92, ddimer=560, threshold=500, expected_tier="low")
wells("64F, leg swelling with dyspnea, HR 88, cancer; alternative dx less likely.",
      CTPA, SRC_GDL_IMG, "Atypical/typical with risk and PE most likely -> high tier -> CTPA",
      age=64, resp=("dyspnea",), assoc=("legSymptoms",), risk=("cancer",), altDx="lessLikely",
      expected_tier="high")
wells("27F, pleuritic pain only, oral contraceptives; alternative dx as likely.",
      RULED_OUT, SRC_PERC, "Estrogen use entered fresh at PERC -> D-dimer path", age=27,
      resp=("pleuritic",), perc_new=("estrogenUse",), ddimer=300, threshold=1000,
      expected_tier="low")
wells("52M, appendicectomy 10 days ago, now pleuritic pain; alternative dx as likely.",
      RULED_OUT, SRC_PERC, "Recent surgery entered fresh at PERC -> D-dimer path", age=52,
      resp=("pleuritic",), perc_new=("recentSurgeryTrauma",), ddimer=300, threshold=1000,
      expected_tier="low")
wells("45M, dyspnea, pleuritic pain, abnormal CXR, HR 100, family history of VTE; alt dx less likely.",
      CTPA, SRC_GDL_IMG, "Typical + risk + PE most likely -> high tier -> CTPA", age=45,
      resp=("dyspnea", "pleuritic"), assoc=("cxr",), hr=100, risk=("familyHx",), altDx="lessLikely",
      expected_tier="high")
wells("70F, non-pleuritic chest pain and dyspnea, HR 91, paralysis; alternative dx as likely.",
      DD_IMAGING, SRC_YEARS, "Moderate tier, YEARS 0 -> <1000, elevated value -> CTPA",
      age=70, resp=("dyspnea", "nonpleuritic"), hr=91, risk=("paralysis",),
      ddimer=1600, threshold=1000, expected_tier="moderate")
wells("36F, post-partum, dyspnea and pleuritic pain, HR 97; alternative dx as likely.",
      RULED_OUT, SRC_YEARS, "Moderate tier, YEARS 0 -> 850 < 1000 -> excluded", age=36,
      resp=("dyspnea", "pleuritic"), hr=97, risk=("postpartum",), ddimer=850, threshold=1000,
      expected_tier="moderate")
wells("58M, leg fracture 3 weeks ago, dyspnea, pleuritic pain, HR 93; alt dx less likely.",
      CTPA, SRC_GDL_IMG, "Typical + risk + PE most likely -> high -> CTPA", age=58,
      resp=("dyspnea", "pleuritic"), hr=93, risk=("fracture",), altDx="lessLikely",
      expected_tier="high")
wells("49F, dyspnea alone, HR 85, no risk factors; alternative dx as likely.",
      NONE_PERC, SRC_PERC, "Low tier, PERC 0/8 at age 49 -> no testing", age=49,
      resp=("dyspnea",), expected_tier="low")
wells("50F, dyspnea alone, HR 85, no risk factors; alternative dx as likely.",
      RULED_OUT, SRC_PERC, "Age exactly 50 meets the PERC age criterion -> D-dimer path",
      age=50, resp=("dyspnea",), ddimer=400, threshold=1000, expected_tier="low")
wells("40M, HR exactly 100 with pleuritic pain; no risk; alternative dx as likely.",
      RULED_OUT, SRC_PERC, "HR exactly 100 meets the PERC tachycardia criterion",
      age=40, resp=("pleuritic",), hr=100, ddimer=400, threshold=1000, expected_tier="low")
wells("40M, room-air SpO2 exactly 95% with pleuritic pain; no risk; alternative dx as likely.",
      NONE_PERC, SRC_PERC, "SpO2 95% does NOT meet the PERC criterion (<95%) -> PERC 0/8",
      age=40, resp=("pleuritic",), raSpo2=95, expected_tier="low")
wells("40M, room-air SpO2 94% with pleuritic pain; no risk; alternative dx as likely.",
      RULED_OUT, SRC_PERC, "SpO2 94% meets the PERC criterion (<95%)", age=40,
      resp=("pleuritic",), raSpo2=94, ddimer=400, threshold=1000, expected_tier="low")
wells("44F, HR 99 with pleuritic pain; no risk; alternative dx as likely.",
      NONE_PERC, SRC_PERC, "HR 99 does not meet the PERC tachycardia criterion -> PERC 0/8",
      age=44, resp=("pleuritic",), hr=99, expected_tier="low")

# =====================================================================
# BLOCK I — Age-adjusted D-dimer  [ADVISORY]
# The guideline endorses age x 10 as an alternative at low/intermediate
# probability. The app implements YEARS adjustment only. These cases
# record what the app does where the two strategies diverge.
# =====================================================================
_age_note = ("The 2026 AHA/ACC guideline lists an age-adjusted threshold (age x 10 ug/L FEU "
             "for patients >50) as a Class 2a alternative. The app applies the YEARS "
             "adjustment only, so for an older patient with >=1 YEARS item it uses 500 "
             "where age adjustment would allow a higher cut-off. Both strategies are "
             "endorsed; this is a documented scope choice, not a defect.")
gestalt("78M, intermediate probability, DVT signs, D-dimer 700 (below age-adjusted 780, above 500).",
        "intermediate", DD_IMAGING, SRC_GDL_AGEADJ,
        "YEARS threshold 500 -> imaging; age-adjusted 780 would have excluded PE",
        age=78, years=("dvt",), ddimer=700, threshold=500, advisory=True, note=_age_note)
gestalt("85F, intermediate probability, PE most likely, D-dimer 800 (below age-adjusted 850).",
        "intermediate", DD_IMAGING, SRC_GDL_AGEADJ,
        "YEARS threshold 500 -> imaging; age-adjusted 850 would have excluded PE",
        age=85, years=("peMostLikely",), ddimer=800, threshold=500, advisory=True, note=_age_note)
gestalt("66M, intermediate probability, hemoptysis, D-dimer 640 (below age-adjusted 660).",
        "intermediate", DD_IMAGING, SRC_GDL_AGEADJ,
        "YEARS threshold 500 -> imaging; age-adjusted 660 would have excluded PE",
        age=66, years=("hemoptysis",), ddimer=640, threshold=500, advisory=True, note=_age_note)
wells("80F, moderate tier, PE most likely, D-dimer 750 (below age-adjusted 800).",
      DD_IMAGING, SRC_GDL_AGEADJ,
      "YEARS threshold 500 -> imaging; age-adjusted 800 would have excluded PE",
      age=80, altDx="lessLikely", ddimer=750, threshold=500, expected_tier="moderate",
      advisory=True, note=_age_note)
wells("72M, moderate tier with leg swelling, D-dimer 690 (below age-adjusted 720).",
      DD_IMAGING, SRC_GDL_AGEADJ,
      "YEARS threshold 500 -> imaging; age-adjusted 720 would have excluded PE",
      age=72, resp=("dyspnea", "pleuritic"), assoc=("legSymptoms",), hr=95, risk=("cancer",),
      ddimer=690, threshold=500, expected_tier="moderate", advisory=True, note=_age_note)


def main():
    with open("cases.json", "w") as f:
        json.dump(CASES, f, indent=2)
    binding = [c for c in CASES if not c["advisory"]]
    advisory = [c for c in CASES if c["advisory"]]
    tally = {}
    for c in CASES:
        r = c["expected"]["recommendation"]
        tally[r] = tally.get(r, 0) + 1
    print(f"Wrote cases.json: {len(CASES)} cases "
          f"({len(binding)} binding, {len(advisory)} advisory).")
    print(f"  Gestalt pathway: {sum(1 for c in CASES if c['pathway'] == 'gestalt')}, "
          f"Wells pathway: {sum(1 for c in CASES if c['pathway'] == 'wells')}")
    print("Expected-recommendation distribution:")
    for k in sorted(tally):
        print(f"  {k}: {tally[k]}")


if __name__ == "__main__":
    main()
