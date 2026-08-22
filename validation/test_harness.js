"use strict";
/**
 * Validation harness for the Acute PE Predictor app.
 *
 * Generates 100 synthetic patients with randomized clinical characteristics,
 * then computes the pretest probability two different, independently written
 * ways:
 *
 *   1. appCompute()       — the exact logic copied verbatim from the app's
 *                            compute() and autoShock() functions in index.html
 *                            (same control flow, same variable names).
 *
 *   2. referenceCompute() — a fresh re-derivation of the Wells 1998 algorithm
 *                            (Figure 1) written independently as an explicit
 *                            lookup table instead of nested if/else, so a
 *                            structural bug in one style is unlikely to be
 *                            reproduced by accident in the other.
 *
 * Agreement between the two on all 100 patients is evidence the app's code
 * correctly implements the decision logic as documented; any disagreement
 * pinpoints an exact patient profile to debug.
 *
 * IMPORTANT SCOPE NOTE: both implementations encode the SAME reading of the
 * original 1998 Figure 1 decision tree (respiratory-point counting, the
 * typical/atypical/severe split, and the alternative-diagnosis + risk-factor
 * branch table). This harness therefore validates that the CODE correctly
 * implements that reading — it does not independently re-verify the reading
 * itself against the original journal figure. See VALIDATION_REPORT.md.
 */

const RESP_POINT_KEYS = ["dyspnea", "pleuritic", "hemoptysis", "nonpleuritic", "pleuralRub", "cxr"];
const RISK_KEYS = ["surgery", "immobilization", "priorVte", "fracture", "familyHx", "cancer", "postpartum", "paralysis"];

// ---------------------------------------------------------------------------
// 1. appCompute — copied verbatim from index.html's compute()/autoShock()
// ---------------------------------------------------------------------------
function appAutoShock(state) {
  const hr = state.hr, sbp = state.sbp, fio2Correct = state.fio2Correct, vent = !!state.assoc.ventilated;
  if (sbp == null || sbp === "") return false;
  if (sbp >= 90) return false;
  const tachy = hr != null && hr > 100;
  const highO2 = fio2Correct != null && fio2Correct >= 40;
  return !!(tachy || vent || highO2);
}

function appCompute(state) {
  const checkedCount = RESP_POINT_KEYS.reduce((n, k) => n + ((state.resp[k] || state.assoc[k]) ? 1 : 0), 0);
  const hypoxia = state.raSpo2 != null && state.raSpo2 < 92 && state.fio2Correct != null && state.fio2Correct < 40;
  const respCount = checkedCount + (hypoxia ? 1 : 0);
  const cxr = !!(state.resp.cxr || state.assoc.cxr);
  const hr = state.hr;
  const typicalSecondary = (hr != null && hr > 90) || !!state.assoc.legSymptoms || !!state.assoc.lowFever || cxr;
  const isTypical = respCount >= 2 && typicalSecondary;
  const hasSymptoms = respCount >= 1 || (hr != null && hr > 90);

  const shock = appAutoShock(state);
  const severeCriteria = !!state.resp.syncope || shock || (!!state.assoc.jvp && (!!state.assoc.s1q3t3 || !!state.assoc.rbbb));

  let category;
  if (severeCriteria) category = "severe";
  else if (isTypical) category = "typical";
  else if (hasSymptoms) category = "atypical";
  else category = "atypical";

  const riskPresent = RISK_KEYS.some((k) => !!state.risk[k]);
  const altDx = state.altDx;

  let pretest = null;
  if (altDx) {
    if (category === "severe") {
      pretest = altDx === "lessLikely" ? "high" : "moderate";
    } else if (category === "typical") {
      if (altDx === "asLikely") pretest = riskPresent ? "moderate" : "low";
      else pretest = riskPresent ? "high" : "moderate";
    } else {
      if (altDx === "asLikely") pretest = "low";
      else pretest = riskPresent ? "high" : "moderate";
    }
  }

  return { respCount, isTypical, hasSymptoms, severeCriteria, shock, category, riskPresent, altDx, pretest };
}

// ---------------------------------------------------------------------------
// 2. referenceCompute — independent re-derivation, table-driven instead of
//    nested if/else, written without looking at appCompute's control flow.
// ---------------------------------------------------------------------------
const BRANCH_TABLE = {
  // category -> altDx -> riskPresent -> pretest
  typical: {
    asLikely:   { true: "moderate", false: "low" },
    lessLikely: { true: "high",     false: "moderate" },
  },
  atypical: {
    asLikely:   { true: "low",  false: "low" },
    lessLikely: { true: "high", false: "moderate" },
  },
  severe: {
    // risk factors are not consulted once severity criteria are met
    asLikely:   { true: "moderate", false: "moderate" },
    lessLikely: { true: "high",     false: "high" },
  },
};

function referenceCompute(state) {
  // --- respiratory point tally (7 possible points total) ---
  let points = 0;
  for (const k of RESP_POINT_KEYS) {
    const present = Boolean(state.resp[k]) || Boolean(state.assoc[k]);
    if (present) points += 1;
  }
  const hypoxiaPresent =
    typeof state.raSpo2 === "number" &&
    typeof state.fio2Correct === "number" &&
    state.raSpo2 < 92 &&
    state.fio2Correct < 40;
  if (hypoxiaPresent) points += 1;

  // --- "typical" secondary criterion: at least one supporting sign ---
  const cxrPresent = Boolean(state.resp.cxr) || Boolean(state.assoc.cxr);
  const supportingSign =
    (typeof state.hr === "number" && state.hr > 90) ||
    Boolean(state.assoc.legSymptoms) ||
    Boolean(state.assoc.lowFever) ||
    cxrPresent;
  const meetsTypical = points >= 2 && supportingSign;
  const anySymptom = points >= 1 || (typeof state.hr === "number" && state.hr > 90);

  // --- severe / acute cor pulmonale criteria ---
  const hypotensive = typeof state.sbp === "number" && state.sbp < 90;
  const shockCompanion =
    (typeof state.hr === "number" && state.hr > 100) ||
    Boolean(state.assoc.ventilated) ||
    (typeof state.fio2Correct === "number" && state.fio2Correct >= 40);
  const shockPresent = hypotensive && shockCompanion;
  const rightHeartStrain = Boolean(state.assoc.jvp) && (Boolean(state.assoc.s1q3t3) || Boolean(state.assoc.rbbb));
  const severePresent = Boolean(state.resp.syncope) || shockPresent || rightHeartStrain;

  // --- presentation shape ---
  let shape;
  if (severePresent) shape = "severe";
  else if (meetsTypical) shape = "typical";
  else shape = "atypical"; // covers both "atypical" and "no symptoms" fallback

  // --- clinical judgment inputs ---
  const anyRiskFactor = RISK_KEYS.some((k) => Boolean(state.risk[k]));
  const altDx = state.altDx;

  let pretest = null;
  if (altDx === "asLikely" || altDx === "lessLikely") {
    pretest = BRANCH_TABLE[shape][altDx][String(anyRiskFactor)];
  }

  return {
    respCount: points,
    isTypical: meetsTypical,
    hasSymptoms: anySymptom,
    severeCriteria: severePresent,
    shock: shockPresent,
    category: shape,
    riskPresent: anyRiskFactor,
    altDx,
    pretest,
  };
}

// ---------------------------------------------------------------------------
// Patient generator — seeded PRNG for reproducibility
// ---------------------------------------------------------------------------
function mulberry32(seed) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function makePatient(rng, i) {
  const bool = (p) => rng() < p;
  const int = (min, max) => Math.round(min + rng() * (max - min));

  const resp = {
    dyspnea: bool(0.45),
    pleuritic: bool(0.3),
    hemoptysis: bool(0.12),
    nonpleuritic: bool(0.2),
    syncope: bool(0.08),
  };
  // pleuralRub and cxr are rendered on step 2 but still write into either
  // bucket depending on which screen holds them; scatter across both
  // buckets on purpose to exercise the resp||assoc lookup in both functions.
  const pleuralRubInResp = bool(0.5);
  const cxrInResp = bool(0.5);

  const assoc = {
    ventilated: bool(0.05),
    lowFever: bool(0.18),
    legSymptoms: bool(0.22),
    jvp: bool(0.12),
    s1q3t3: bool(0.08),
    rbbb: bool(0.08),
  };
  if (!pleuralRubInResp) assoc.pleuralRub = bool(0.25);
  else resp.pleuralRub = true;
  if (!cxrInResp) assoc.cxr = bool(0.3);
  else resp.cxr = true;

  const risk = {};
  for (const k of RISK_KEYS) risk[k] = bool(0.14);

  // A handful of deliberate boundary cases mixed into the random set to
  // stress-test the edge conditions (>, >=, <, <=) rather than pure chance.
  let hr = int(50, 160);
  let sbp = int(70, 180);
  let raSpo2 = int(84, 100);
  let fio2Correct = bool(0.6) ? int(21, 100) : null;

  if (i === 0) { hr = 90; sbp = 90; raSpo2 = 92; fio2Correct = 40; }       // all-equal boundary
  if (i === 1) { hr = 91; sbp = 89; raSpo2 = 91; fio2Correct = 39; }       // just past each boundary
  if (i === 2) { raSpo2 = 92; fio2Correct = null; }                       // hypoxia not evaluable
  if (i === 3) { sbp = 85; hr = 95; fio2Correct = null; assoc.ventilated = false; } // shock via tachycardia only
  if (i === 4) { sbp = 85; hr = 60; fio2Correct = null; assoc.ventilated = true; }  // shock via ventilation only

  const altDx = bool(0.5) ? "asLikely" : "lessLikely";

  return { resp, assoc, risk, hr, sbp, raSpo2, fio2Correct, altDx };
}

// ---------------------------------------------------------------------------
// Run
// ---------------------------------------------------------------------------
const SEED = 20260822; // date-derived, fixed for reproducibility
const rng = mulberry32(SEED);
const N = 100;

const rows = [];
let matches = 0;
const mismatches = [];

for (let i = 0; i < N; i++) {
  const patient = makePatient(rng, i);
  const app = appCompute(patient);
  const ref = referenceCompute(patient);
  const isMatch = app.category === ref.category && app.pretest === ref.pretest;
  if (isMatch) matches++;
  else mismatches.push({ i, patient, app, ref });

  rows.push({
    id: i + 1,
    hr: patient.hr,
    sbp: patient.sbp,
    raSpo2: patient.raSpo2,
    fio2Correct: patient.fio2Correct,
    respCount_app: app.respCount,
    respCount_ref: ref.respCount,
    category_app: app.category,
    category_ref: ref.category,
    altDx: patient.altDx,
    riskPresent_app: app.riskPresent,
    pretest_app: app.pretest,
    pretest_ref: ref.pretest,
    match: isMatch ? "YES" : "NO",
  });
}

// Confusion matrix (app rows vs reference columns)
const cats = ["low", "moderate", "high"];
const confusion = {};
for (const a of cats) { confusion[a] = {}; for (const b of cats) confusion[a][b] = 0; }
for (const r of rows) {
  if (cats.includes(r.pretest_app) && cats.includes(r.pretest_ref)) {
    confusion[r.pretest_app][r.pretest_ref]++;
  }
}

const distApp = { low: 0, moderate: 0, high: 0 };
const distRef = { low: 0, moderate: 0, high: 0 };
for (const r of rows) {
  if (distApp[r.pretest_app] !== undefined) distApp[r.pretest_app]++;
  if (distRef[r.pretest_ref] !== undefined) distRef[r.pretest_ref]++;
}

console.log(JSON.stringify({
  n: N,
  matches,
  mismatchCount: mismatches.length,
  accuracyPct: ((matches / N) * 100).toFixed(1),
  distApp,
  distRef,
  confusion,
  mismatches,
  rows,
}, null, 2));
