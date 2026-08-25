// Drives the ACTUAL Acute PE Predictor app (index.html) as a black box,
// through Playwright/Chromium, for every patient in patients.json, and
// records what the deployed app itself computes. This is compared against
// generate_reference.py's independently-written reference implementation
// (a separate script, a separate language, reasoning from the spec rather
// than from the app's own source) in compare_results.py.
//
// For speed, each patient's entire click-through is done inside a single
// page.evaluate() call that manipulates the real DOM elements and dispatches
// the same events the app's own listeners expect (change/input/click) —
// this is still exercising the app's actual production code (its real
// event handlers, its real compute()/render functions), just without the
// per-action IPC round-trip and actionability-polling overhead of calling
// page.check()/page.fill()/page.click() one at a time.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const APP_URL = 'file://' + path.resolve(__dirname, '..', 'index.html');
const PATIENTS = JSON.parse(fs.readFileSync(path.join(__dirname, 'patients.json'), 'utf8'));

const RESP_KEYS = ["syncope", "dyspnea", "pleuritic", "hemoptysis", "nonpleuritic"];
const ASSOC_KEYS = ["ventilated", "lowFever", "legSymptoms", "pleuralRub", "jvp", "s1q3t3", "rbbb", "cxr"];
const RISK_KEYS = ["surgery", "immobilization", "priorVte", "fracture", "familyHx", "cancer", "postpartum", "paralysis"];

async function runPatient(page, p) {
  await page.goto(APP_URL, { waitUntil: 'domcontentloaded' });

  const result = await page.evaluate((args) => {
    const { p, RESP_KEYS, ASSOC_KEYS, RISK_KEYS } = args;

    function setCheck(id, on) {
      if (!on) return;
      var el = document.getElementById(id);
      if (!el) throw new Error('missing checkbox ' + id);
      el.checked = true;
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }
    function setNum(id, val) {
      var el = document.getElementById(id);
      el.value = String(val);
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }
    function click(sel) {
      var el = typeof sel === 'string' ? document.querySelector(sel) : sel;
      if (!el) throw new Error('missing element ' + sel);
      el.click();
    }

    // Home -> Step 1
    click('[data-go="resp"]');
    RESP_KEYS.forEach(function(k){ setCheck('chk-' + k, p.resp[k]); });
    click('#scr-resp [data-go="assoc"]');

    // Step 2
    setNum('f-hr', p.hr);
    setNum('f-sbp', p.sbp);
    setNum('f-raSpo2', p.raSpo2);
    setNum('f-fio2Correct', p.fio2Correct);
    ASSOC_KEYS.forEach(function(k){ setCheck('chk-' + k, p.assoc[k]); });
    click('#btn-continue-assoc');

    // Step 3
    RISK_KEYS.forEach(function(k){ setCheck('chk-' + k, p.risk[k]); });
    click('#seg-altdx [data-val="' + p.altDx + '"]');
    click('#btn-see-results');

    // Results
    var tagText = document.getElementById('result-tag-text').textContent;
    var pretest = /^Low/i.test(tagText) ? 'low' : /^Moderate/i.test(tagText) ? 'moderate' : /^High/i.test(tagText) ? 'high' : null;
    var reasoningLines = Array.prototype.map.call(
      document.querySelectorAll('#reasoning-list .reasoning-item span:nth-child(2)'),
      function(e){ return e.textContent; }
    );

    var out = { id: p.id, appPretest: pretest, appReasoning: reasoningLines, appPerc: null, appYears: null };

    var nextGo = document.getElementById('btn-next-step').getAttribute('data-go');

    if (nextGo === 'perc') {
      click('#btn-next-step');
      setNum('f-age', p.age);
      setCheck('chk-estrogenUse', p.estrogenUse);
      setCheck('chk-recentSurgeryTrauma', p.recentSurgeryTrauma);
      var scoreText = document.getElementById('perc-score-pill').textContent;
      var m = scoreText.match(/(\d+)\s*\/\s*8/);
      var btnGo = document.getElementById('btn-perc-continue').getAttribute('data-go');
      out.appPerc = { score: m ? parseInt(m[1], 10) : null, negative: btnGo === 'final-perc' };
    } else if (nextGo === 'ddimer') {
      click('#btn-next-step');
      var pretext = document.getElementById('ddimer-pretext').textContent;
      var val = document.getElementById('ddimer-threshold-value').textContent;
      var ym = pretext.match(/YEARS\s+(\d+)\/3/);
      var thresholdMatch = val.match(/(\d+)/);
      out.appYears = { itemCount: ym ? parseInt(ym[1], 10) : null, threshold: thresholdMatch ? parseInt(thresholdMatch[1], 10) : null };
    }
    // nextGo === 'final-imaging' (high pretest): pretest already captured.

    return out;
  }, { p, RESP_KEYS, ASSOC_KEYS, RISK_KEYS });

  return result;
}

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const page = await browser.newPage();
  const results = [];
  const start = Date.now();

  for (const p of PATIENTS) {
    try {
      const r = await runPatient(page, p);
      results.push(r);
    } catch (err) {
      results.push({ id: p.id, error: String(err && err.message || err) });
    }
    if (p.id % 50 === 0) {
      const elapsed = ((Date.now() - start) / 1000).toFixed(1);
      console.log(`...${p.id}/${PATIENTS.length} patients run (${elapsed}s elapsed)`);
    }
  }

  await browser.close();
  fs.writeFileSync(path.join(__dirname, 'app_results.json'), JSON.stringify(results, null, 1));
  const totalTime = ((Date.now() - start) / 1000).toFixed(1);
  console.log(`Done. ${results.length} patients run in ${totalTime}s. Wrote app_results.json`);
})();
