// Drives the actual deployed index.html (headless Chromium via Playwright)
// end to end for every patient in patients.json -- 100 through the Wells
// Expanded Criteria Pathway and 100 through the Clinical Gestalt Pathway --
// and records the app's FINAL RECOMMENDATION, read straight off the outcome
// screen's rendered text, not from any internal JS state.
//
// The driver never predicts where the app should route a patient: it clicks
// whatever "Continue" button the app shows and then looks at which screen it
// landed on. So the route itself (PERC vs D-dimer vs straight to imaging) is
// the app's answer, not an assumption baked into the harness.
//
// Run with: node run_app_validation.js   (requires `playwright`)

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const url = 'file://' + path.resolve(__dirname, '..', 'index.html');

// Maps the outcome screen's rendered title/body onto the five recommendation
// categories the reference implementation scores.
function readRecommendation(title, body) {
  const t = title.trim();
  if (t === 'PE Ruled Out — PERC Negative') return 'none_perc_negative';
  if (t === 'PE Ruled Out') return 'ddimer_ruled_out';
  if (t === 'Unstable — Consider Bedside TTE') return 'bedside_tte';
  if (t === 'Imaging Indicated') {
    return body.trim().startsWith('High pretest probability of PE.') ? 'ctpa_direct' : 'ddimer_imaging';
  }
  throw new Error(`unrecognized outcome title "${t}"`);
}

function parseThreshold(text) {
  const m = text.match(/(\d+)/);
  return m ? Number(m[1]) : null;
}

async function activeScreen(page) {
  return page.$eval('.screen.active', el => el.getAttribute('data-screen'));
}

async function runWells(page, p) {
  await page.goto(url);
  await page.waitForSelector('#scr-home.active');

  await page.click('[data-go="resp"]');
  await page.waitForSelector('#scr-resp.active');
  for (const key of Object.keys(p.resp)) {
    if (p.resp[key]) await page.click(`#resp-list [data-key="${key}"]`);
  }

  await page.click('[data-go="assoc"]');
  await page.waitForSelector('#scr-assoc.active');
  await page.fill('#f-sbp', String(p.sbp));
  await page.fill('#f-hr', String(p.hr));
  await page.fill('#f-raSpo2', String(p.raSpo2));
  if (p.fio2Correct != null) await page.fill('#f-fio2Correct', String(p.fio2Correct));
  for (const key of Object.keys(p.assoc)) {
    if (p.assoc[key]) await page.click(`#assoc-list [data-key="${key}"]`);
  }
  if (await page.getAttribute('#btn-continue-assoc', 'disabled') !== null) {
    throw new Error(`btn-continue-assoc disabled (sbp=${p.sbp} hr=${p.hr} raSpo2=${p.raSpo2} fio2=${p.fio2Correct})`);
  }
  await page.click('#btn-continue-assoc');
  await page.waitForSelector('#scr-judgment.active');

  for (const key of Object.keys(p.risk)) {
    if (p.risk[key]) await page.click(`#risk-list [data-key="${key}"]`);
  }
  await page.click(`#altdx-list [data-key="${p.altDx}"]`);
  await page.click('#btn-see-results');
  await page.waitForSelector('#scr-results.active');

  const tagMap = { 'Low probability': 'low', 'Moderate probability': 'moderate', 'High probability': 'high' };
  const appPretest = tagMap[(await page.textContent('#result-tag-text')).trim()];
  if (!appPretest) throw new Error('unrecognized pretest tag');

  const out = { appPretest, appPercScore: null, appThreshold: null, route: ['results'] };

  await page.click('#btn-next-step');
  await page.waitForSelector('.screen.active');
  let screen = await activeScreen(page);

  if (screen === 'perc') {
    out.route.push('perc');
    await page.fill('#f-age', String(p.age));
    for (const key of Object.keys(p.percNew)) {
      if (p.percNew[key]) await page.click(`#perc-new-list [data-key="${key}"]`);
    }
    out.appPercScore = Number((await page.textContent('#perc-score-pill')).split('/')[0].trim());
    await page.click('#btn-perc-continue');
    await page.waitForTimeout(50);
    screen = await activeScreen(page);
  }

  if (screen === 'ddimer') {
    out.route.push('ddimer');
    out.appThreshold = parseThreshold(await page.textContent('#ddimer-threshold-value'));
    await page.fill('#f-ddimer', String(p.ddimer));
    await page.click('#btn-interpret');
    await page.waitForTimeout(50);
    screen = await activeScreen(page);
  }

  if (screen !== 'final') throw new Error(`expected final screen, got "${screen}"`);
  out.route.push('final');
  out.appRecommendation = readRecommendation(
    await page.textContent('#outcome-title'),
    await page.textContent('#outcome-body')
  );
  return out;
}

async function runGestalt(page, p) {
  await page.goto(url);
  await page.waitForSelector('#scr-home.active');

  await page.click('[data-go="gw-gestalt"]');
  await page.waitForSelector('#scr-gw-gestalt.active');
  await page.click(`#scr-gw-gestalt .tier-card[data-tier="${p.gestaltPick}"]`);
  await page.waitForSelector('#scr-gw-result.active');

  const tagMap = { 'Low probability': 'low', 'Intermediate probability': 'intermediate', 'High probability': 'high' };
  const appPretest = tagMap[(await page.textContent('#gw-result-tag-text')).trim()];
  if (!appPretest) throw new Error('unrecognized pretest tag');

  const out = { appPretest, appPercScore: null, appThreshold: null, route: ['gw-result'] };

  await page.click('#gw-btn-next-step');
  await page.waitForSelector('.screen.active');
  let screen = await activeScreen(page);

  if (screen === 'gw-perc') {
    out.route.push('gw-perc');
    await page.fill('#f-gw-age', String(p.age));
    for (const key of Object.keys(p.gwPerc)) {
      if (p.gwPerc[key]) await page.click(`#gw-perc-fresh-list [data-key="${key}"]`);
    }
    out.appPercScore = Number((await page.textContent('#gw-perc-score-pill')).split('/')[0].trim());
    await page.click('#gw-btn-perc-continue');
    await page.waitForTimeout(50);
    screen = await activeScreen(page);
  }

  if (screen === 'gw-ddimer') {
    out.route.push('gw-ddimer');
    for (const key of Object.keys(p.gwYears)) {
      if (p.gwYears[key]) await page.click(`#gw-years-list [data-key="${key}"]`);
    }
    out.appThreshold = parseThreshold(await page.textContent('#gw-ddimer-threshold-value'));
    await page.fill('#f-gw-ddimer', String(p.ddimer));
    await page.click('#gw-btn-interpret');
    await page.waitForTimeout(50);
    screen = await activeScreen(page);
  }

  if (screen === 'gw-instability') {
    out.route.push('gw-instability');
    await page.fill('#f-gw-sbp', String(p.instability.sbp));
    await page.fill('#f-gw-hr', String(p.instability.hr));
    if (p.instability.fio2Correct != null) await page.fill('#f-gw-fio2Correct', String(p.instability.fio2Correct));
    if (p.instability.vent) await page.click('#gw-instability-vent-list [data-key="vent"]');
    await page.click('#gw-btn-instability-continue');
    await page.waitForTimeout(50);
    screen = await activeScreen(page);
  }

  if (screen !== 'gw-final') throw new Error(`expected gw-final screen, got "${screen}"`);
  out.route.push('gw-final');
  out.appRecommendation = readRecommendation(
    await page.textContent('#gw-outcome-title'),
    await page.textContent('#gw-outcome-body')
  );
  return out;
}

(async () => {
  const patients = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'patients.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const consoleErrors = [];
  page.on('pageerror', (err) => consoleErrors.push(err.message));
  page.on('console', (msg) => {
    if (msg.type() === 'error' && !msg.text().includes('ERR_TUNNEL') && !msg.text().includes('net::')) {
      consoleErrors.push(msg.text());
    }
  });

  const results = [];
  const startTime = Date.now();
  for (const p of patients) {
    try {
      const r = p.pathway === 'wells' ? await runWells(page, p) : await runGestalt(page, p);
      results.push({ id: p.id, pathway: p.pathway, ...r, error: null });
    } catch (e) {
      results.push({ id: p.id, pathway: p.pathway, appPretest: null, appPercScore: null,
                     appThreshold: null, route: null, appRecommendation: null, error: e.message });
    }
    if (p.id % 25 === 0) {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(0);
      console.log(`  ...${p.id}/${patients.length} patients run (${elapsed}s elapsed)`);
    }
  }

  await browser.close();
  fs.writeFileSync(path.resolve(__dirname, 'app_results.json'), JSON.stringify(results, null, 2));

  const errored = results.filter(r => r.error);
  console.log(`\nDone. ${results.length} patients run, ${errored.length} errored, ${consoleErrors.length} console/page errors captured.`);
  if (errored.length) console.log('Errored patients:', errored.map(r => r.id).join(', '));
  if (consoleErrors.length) consoleErrors.slice(0, 10).forEach(e => console.log('  CONSOLE ERROR: ' + e));
  console.log('Wrote app_results.json');
})();
