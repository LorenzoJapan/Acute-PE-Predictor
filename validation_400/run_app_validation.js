// Drives the actual deployed index.html (headless Chromium via Playwright)
// through the Wells Expanded Criteria Pathway's Steps 1-3 for every patient
// in patients.json, and records what the app itself computes as the
// pretest probability (Low / Moderate / High), reading it straight off the
// results screen -- not from any internal JS state -- so this is a real UI
// black-box check, not a shortcut into the app's own functions.
//
// Run with: node run_app_validation.js   (requires `playwright`)

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const url = 'file://' + path.resolve(__dirname, '..', 'index.html');

async function runPatient(page, patient) {
  await page.goto(url);
  await page.waitForSelector('#scr-home.active');

  await page.click('[data-go="resp"]');
  await page.waitForSelector('#scr-resp.active');
  for (const key of Object.keys(patient.resp)) {
    if (patient.resp[key]) {
      await page.click(`#resp-list [data-key="${key}"]`);
    }
  }

  await page.click('[data-go="assoc"]');
  await page.waitForSelector('#scr-assoc.active');
  await page.fill('#f-sbp', String(patient.sbp));
  await page.fill('#f-hr', String(patient.hr));
  await page.fill('#f-raSpo2', String(patient.raSpo2));
  if (patient.fio2Correct != null) {
    await page.fill('#f-fio2Correct', String(patient.fio2Correct));
  }
  for (const key of Object.keys(patient.assoc)) {
    if (patient.assoc[key]) {
      await page.click(`#assoc-list [data-key="${key}"]`);
    }
  }

  const contBtn = page.locator('#btn-continue-assoc');
  const contDisabled = await contBtn.getAttribute('disabled');
  if (contDisabled !== null) {
    throw new Error(`Patient ${patient.id}: btn-continue-assoc still disabled (sbp=${patient.sbp} hr=${patient.hr} raSpo2=${patient.raSpo2} fio2Correct=${patient.fio2Correct})`);
  }
  await contBtn.click();
  await page.waitForSelector('#scr-judgment.active');

  for (const key of Object.keys(patient.risk)) {
    if (patient.risk[key]) {
      await page.click(`#risk-list [data-key="${key}"]`);
    }
  }
  await page.click(`#seg-altdx [data-val="${patient.altDx}"]`);

  const seeBtn = page.locator('#btn-see-results');
  const seeDisabled = await seeBtn.getAttribute('disabled');
  if (seeDisabled !== null) {
    throw new Error(`Patient ${patient.id}: btn-see-results still disabled`);
  }
  await seeBtn.click();
  await page.waitForSelector('#scr-results.active');

  const tagText = (await page.textContent('#result-tag-text')).trim();
  const map = { 'Low probability': 'low', 'Moderate probability': 'moderate', 'High probability': 'high' };
  const appPretest = map[tagText];
  if (!appPretest) {
    throw new Error(`Patient ${patient.id}: unrecognized result tag text "${tagText}"`);
  }
  return appPretest;
}

(async () => {
  const patients = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'patients.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const consoleErrors = [];
  page.on('pageerror', (err) => consoleErrors.push({ msg: err.message }));
  page.on('console', (msg) => {
    if (msg.type() === 'error' && !msg.text().includes('ERR_TUNNEL') && !msg.text().includes('net::')) {
      consoleErrors.push({ msg: msg.text() });
    }
  });

  const results = [];
  const startTime = Date.now();
  for (const patient of patients) {
    try {
      const appPretest = await runPatient(page, patient);
      results.push({ id: patient.id, appPretest, error: null });
    } catch (e) {
      results.push({ id: patient.id, appPretest: null, error: e.message });
    }
    if (patient.id % 50 === 0) {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(0);
      console.log(`  ...${patient.id}/${patients.length} patients run (${elapsed}s elapsed)`);
    }
  }

  await browser.close();

  fs.writeFileSync(path.resolve(__dirname, 'app_results.json'), JSON.stringify(results, null, 2));

  const errored = results.filter(r => r.error);
  console.log(`\nDone. ${results.length} patients run, ${errored.length} errored, ${consoleErrors.length} console/page errors captured.`);
  if (errored.length) {
    console.log('Errored patients:', errored.map(r => r.id).join(', '));
  }
  if (consoleErrors.length) {
    consoleErrors.slice(0, 10).forEach(e => console.log('  CONSOLE ERROR: ' + e.msg));
  }
  console.log('Wrote app_results.json');
})();
