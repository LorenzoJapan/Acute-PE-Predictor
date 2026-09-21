// Runs the 100 guideline-anchored golden cases in cases.json against the real
// UI of index.html (headless Chromium via Playwright), and writes
// GOLDEN_REPORT.md and golden_results.csv.
//
// Every expected answer in cases.json was written by hand from the primary
// literature and the 2026 AHA/ACC PE guideline, not derived from the app's
// code -- so a failure here means the app disagrees with the guideline, not
// merely with a transcription of itself.
//
// As in validation_200/, the driver never predicts the route: it clicks
// whichever Continue button the app presents and records which screen it
// lands on.
//
// Run with: node run_golden_cases.js   (requires `playwright`)

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const url = 'file://' + path.resolve(__dirname, '..', 'index.html');

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

const parseThreshold = (text) => { const m = text.match(/(\d+)/); return m ? Number(m[1]) : null; };
const activeScreen = (page) => page.$eval('.screen.active', el => el.getAttribute('data-screen'));

async function runGestalt(page, c) {
  await page.goto(url);
  await page.waitForSelector('#scr-home.active');
  await page.click('[data-go="gw-gestalt"]');
  await page.waitForSelector('#scr-gw-gestalt.active');
  await page.click(`#scr-gw-gestalt .tier-card[data-tier="${c.gestaltPick}"]`);
  await page.waitForSelector('#scr-gw-result.active');

  const tierMap = { 'Low probability': 'low', 'Intermediate probability': 'intermediate', 'High probability': 'high' };
  const out = { appTier: tierMap[(await page.textContent('#gw-result-tag-text')).trim()],
                appPerc: null, appThreshold: null, route: [] };

  await page.click('#gw-btn-next-step');
  let screen = await activeScreen(page);

  if (screen === 'gw-perc') {
    out.route.push('PERC');
    await page.fill('#f-gw-age', String(c.age));
    for (const k of Object.keys(c.gwPerc)) if (c.gwPerc[k]) await page.click(`#gw-perc-fresh-list [data-key="${k}"]`);
    out.appPerc = Number((await page.textContent('#gw-perc-score-pill')).split('/')[0].trim());
    await page.click('#gw-btn-perc-continue');
    await page.waitForTimeout(50);
    screen = await activeScreen(page);
  }
  if (screen === 'gw-ddimer') {
    out.route.push('D-dimer');
    for (const k of Object.keys(c.gwYears)) if (c.gwYears[k]) await page.click(`#gw-years-list [data-key="${k}"]`);
    out.appThreshold = parseThreshold(await page.textContent('#gw-ddimer-threshold-value'));
    if (c.ddimer == null) throw new Error('case reached the D-dimer screen but specifies no D-dimer value');
    await page.fill('#f-gw-ddimer', String(c.ddimer));
    await page.click('#gw-btn-interpret');
    await page.waitForTimeout(50);
    screen = await activeScreen(page);
  }
  if (screen === 'gw-instability') {
    out.route.push('Shock assessment');
    await page.fill('#f-gw-sbp', String(c.instability.sbp));
    await page.fill('#f-gw-hr', String(c.instability.hr));
    if (c.instability.fio2Correct != null) await page.fill('#f-gw-fio2Correct', String(c.instability.fio2Correct));
    if (c.instability.vent) await page.click('#gw-instability-vent-list [data-key="vent"]');
    await page.click('#gw-btn-instability-continue');
    await page.waitForTimeout(50);
    screen = await activeScreen(page);
  }
  if (screen !== 'gw-final') throw new Error(`expected gw-final, got "${screen}"`);
  out.appRecommendation = readRecommendation(await page.textContent('#gw-outcome-title'),
                                             await page.textContent('#gw-outcome-body'));
  return out;
}

async function runWells(page, c) {
  await page.goto(url);
  await page.waitForSelector('#scr-home.active');
  await page.click('[data-go="resp"]');
  await page.waitForSelector('#scr-resp.active');
  for (const k of Object.keys(c.resp)) if (c.resp[k]) await page.click(`#resp-list [data-key="${k}"]`);

  await page.click('[data-go="assoc"]');
  await page.waitForSelector('#scr-assoc.active');
  await page.fill('#f-sbp', String(c.sbp));
  await page.fill('#f-hr', String(c.hr));
  await page.fill('#f-raSpo2', String(c.raSpo2));
  if (c.fio2Correct != null) await page.fill('#f-fio2Correct', String(c.fio2Correct));
  for (const k of Object.keys(c.assoc)) if (c.assoc[k]) await page.click(`#assoc-list [data-key="${k}"]`);
  if (await page.getAttribute('#btn-continue-assoc', 'disabled') !== null) {
    throw new Error('Continue disabled on the vitals screen — check the case inputs');
  }
  await page.click('#btn-continue-assoc');
  await page.waitForSelector('#scr-judgment.active');
  for (const k of Object.keys(c.risk)) if (c.risk[k]) await page.click(`#risk-list [data-key="${k}"]`);
  await page.click(`#altdx-list [data-key="${c.altDx}"]`);
  await page.click('#btn-see-results');
  await page.waitForSelector('#scr-results.active');

  const tierMap = { 'Low probability': 'low', 'Moderate probability': 'moderate', 'High probability': 'high' };
  const out = { appTier: tierMap[(await page.textContent('#result-tag-text')).trim()],
                appPerc: null, appThreshold: null, route: [] };

  await page.click('#btn-next-step');
  let screen = await activeScreen(page);

  if (screen === 'perc') {
    out.route.push('PERC');
    await page.fill('#f-age', String(c.age));
    for (const k of Object.keys(c.percNew)) if (c.percNew[k]) await page.click(`#perc-new-list [data-key="${k}"]`);
    out.appPerc = Number((await page.textContent('#perc-score-pill')).split('/')[0].trim());
    await page.click('#btn-perc-continue');
    await page.waitForTimeout(50);
    screen = await activeScreen(page);
  }
  if (screen === 'ddimer') {
    out.route.push('D-dimer');
    out.appThreshold = parseThreshold(await page.textContent('#ddimer-threshold-value'));
    if (c.ddimer == null) throw new Error('case reached the D-dimer screen but specifies no D-dimer value');
    await page.fill('#f-ddimer', String(c.ddimer));
    await page.click('#btn-interpret');
    await page.waitForTimeout(50);
    screen = await activeScreen(page);
  }
  if (screen !== 'final') throw new Error(`expected final, got "${screen}"`);
  out.appRecommendation = readRecommendation(await page.textContent('#outcome-title'),
                                             await page.textContent('#outcome-body'));
  return out;
}

function md(rows, binding, advisory, errored) {
  const pass = binding.filter(r => r.pass).length;
  const acc = binding.length ? (pass / binding.length * 100).toFixed(1) : '0.0';
  const L = [];
  L.push('# Guideline-Anchored Golden Case Report\n');
  L.push('100 hand-built clinical vignettes whose expected recommendation is taken from the ' +
         'primary literature and the 2026 AHA/ACC PE guideline — **not** from `index.html`. ' +
         'Each case carries the citation that dictates its answer, in `cases.json`.\n');
  L.push('Unlike `validation_200/`, which compares the app against a ' +
         'transcription of its own logic, these cases can fail because the app is *clinically* ' +
         'wrong rather than merely self-inconsistent. See `build_cases.py` for what each case ' +
         'can and cannot anchor.\n');
  L.push('## Result\n');
  L.push(`**${pass} / ${binding.length} binding cases passed (${acc}%)**` +
         (errored.length ? `, ${errored.length} errored.` : '.') + '\n');
  L.push(`${advisory.length} advisory cases (cited authorities conflict, or the guideline endorses ` +
         `an option the app documents it does not implement) are listed separately and excluded ` +
         `from this figure.\n`);

  const byBlock = {};
  for (const r of binding) {
    const b = byBlock[r.rule_group] || (byBlock[r.rule_group] = { n: 0, pass: 0 });
    b.n++; if (r.pass) b.pass++;
  }
  L.push('## Binding cases by rule under test\n');
  L.push('| Rule | N | Passed |');
  L.push('|---|---|---|');
  for (const k of Object.keys(byBlock)) L.push(`| ${k} | ${byBlock[k].n} | ${byBlock[k].pass} |`);
  L.push('');

  const fails = binding.filter(r => !r.pass);
  L.push(`## Failures (${fails.length})\n`);
  if (!fails.length) L.push('None.\n');
  else {
    L.push('| # | Vignette | Expected | App | Rule | Source |');
    L.push('|---|---|---|---|---|---|');
    for (const r of fails) {
      L.push(`| ${r.id} | ${r.vignette} | ${r.expected} | ${r.app} | ${r.rule} | ${r.source} |`);
    }
    L.push('');
  }

  L.push(`## Advisory cases (${advisory.length})\n`);
  L.push('These record what the app does where the cited authorities disagree or where an ' +
         'endorsed alternative is out of scope. They are for clinical review, not pass/fail.\n');
  L.push('| # | Vignette | App behavior | Matches the app\'s cited basis? | Issue |');
  L.push('|---|---|---|---|---|');
  for (const r of advisory) {
    L.push(`| ${r.id} | ${r.vignette} | ${r.app} | ${r.pass ? 'yes' : 'NO'} | ${r.note || ''} |`);
  }
  L.push('');

  if (errored.length) {
    L.push(`## Errors (${errored.length})\n`);
    for (const r of errored) L.push(`- Case ${r.id}: ${r.error}`);
    L.push('');
  }

  L.push('## Files\n');
  L.push('- `build_cases.py` — builds `cases.json`; holds every expected answer as a literal, with its citation.');
  L.push('- `cases.json` — the 100 cases.');
  L.push('- `run_golden_cases.js` — drives the real UI and writes this report plus `golden_results.csv`.');
  return L.join('\n') + '\n';
}

function ruleGroup(c) {
  const r = c.expected.recommendation;
  if (r === 'none_perc_negative') return 'PERC rule-out (PERC 0/8 at low probability)';
  if (r === 'ctpa_direct') return 'High probability → CTPA directly';
  if (r === 'bedside_tte') return 'Haemodynamic instability branch';
  if (c.expected.threshold === 500) return 'YEARS-adjusted D-dimer, threshold 500';
  return 'YEARS-adjusted D-dimer, threshold 1000';
}

(async () => {
  const cases = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'cases.json'), 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const consoleErrors = [];
  page.on('pageerror', e => consoleErrors.push(e.message));
  page.on('console', m => {
    if (m.type() === 'error' && !m.text().includes('ERR_TUNNEL') && !m.text().includes('net::')) {
      consoleErrors.push(m.text());
    }
  });

  const rows = [];
  for (const c of cases) {
    try {
      const r = c.pathway === 'gestalt' ? await runGestalt(page, c) : await runWells(page, c);
      rows.push({
        id: c.id, pathway: c.pathway, vignette: c.vignette, advisory: c.advisory,
        rule: c.rule, rule_group: ruleGroup(c), source: c.source, note: c.note,
        expected: c.expected.recommendation, app: r.appRecommendation,
        expected_threshold: c.expected.threshold, app_threshold: r.appThreshold,
        expected_tier: c.expected_tier || c.gestaltPick, app_tier: r.appTier,
        app_perc: r.appPerc, route: r.route.join(' → '),
        pass: c.expected.recommendation === r.appRecommendation &&
              (c.expected.threshold == null || c.expected.threshold === r.appThreshold),
        error: null,
      });
    } catch (e) {
      rows.push({ id: c.id, pathway: c.pathway, vignette: c.vignette, advisory: c.advisory,
                  rule: c.rule, rule_group: ruleGroup(c), source: c.source, note: c.note,
                  expected: c.expected.recommendation, app: null,
                  expected_threshold: c.expected.threshold, app_threshold: null,
                  expected_tier: c.expected_tier || c.gestaltPick, app_tier: null,
                  app_perc: null, route: null, pass: false, error: e.message });
    }
    if (c.id % 20 === 0) console.log(`  ...${c.id}/${cases.length} cases run`);
  }
  await browser.close();

  const errored = rows.filter(r => r.error);
  const binding = rows.filter(r => !r.advisory && !r.error);
  const advisory = rows.filter(r => r.advisory && !r.error);

  const cols = ['id', 'pathway', 'rule_group', 'expected_tier', 'app_tier', 'app_perc',
                'expected_threshold', 'app_threshold', 'expected', 'app', 'pass', 'advisory',
                'route', 'rule', 'source', 'vignette', 'error'];
  const csv = [cols.join(',')].concat(rows.map(r => cols.map(k => {
    const v = r[k] == null ? '' : String(r[k]);
    return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
  }).join(','))).join('\n');
  fs.writeFileSync(path.resolve(__dirname, 'golden_results.csv'), csv + '\n');
  fs.writeFileSync(path.resolve(__dirname, 'GOLDEN_REPORT.md'), md(rows, binding, advisory, errored));

  const pass = binding.filter(r => r.pass).length;
  console.log(`\n${pass}/${binding.length} binding cases passed` +
              ` (${binding.length ? (pass / binding.length * 100).toFixed(1) : 0}%).`);
  console.log(`${advisory.filter(r => r.pass).length}/${advisory.length} advisory cases matched the app's cited basis.`);
  console.log(`${errored.length} errored, ${consoleErrors.length} console/page errors.`);
  if (errored.length) errored.slice(0, 10).forEach(r => console.log(`  case ${r.id}: ${r.error}`));
  console.log('Wrote GOLDEN_REPORT.md and golden_results.csv');
})();
