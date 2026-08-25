// Headless functional test of the new PERC (low) and YEARS (moderate) logic
// added to the Acute PE Predictor. Drives the real UI with Playwright.
const { chromium } = require('playwright');
const path = require('path');

const FILE_URL = 'file://' + path.resolve(__dirname, 'index.html');

async function withPage(fn) {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const page = await browser.newPage();
  await page.goto(FILE_URL);
  try {
    await fn(page);
  } finally {
    await browser.close();
  }
}

async function goHome(page) {
  await page.click('[data-go="resp"]');
}

async function checkRespItems(page, keys) {
  for (const k of keys) await page.check('#chk-' + k);
  await page.click('#scr-resp [data-go="assoc"]');
}

async function fillVitals(page, { hr, sbp, raSpo2, fio2 }) {
  await page.fill('#f-hr', String(hr));
  await page.fill('#f-sbp', String(sbp));
  await page.fill('#f-raSpo2', String(raSpo2));
  if (fio2 != null) await page.fill('#f-fio2Correct', String(fio2));
}

async function checkAssocItems(page, keys) {
  for (const k of keys) await page.check('#chk-' + k);
  await page.click('#btn-continue-assoc');
}

async function checkRiskItems(page, keys) {
  for (const k of keys) await page.check('#chk-' + k);
}

async function pickAltDx(page, val) {
  await page.click('#seg-altdx [data-val="' + val + '"]');
}

async function seeResults(page) {
  await page.click('#btn-see-results');
}

function log(label, ok, detail) {
  console.log((ok ? 'PASS' : 'FAIL') + ' — ' + label + (detail ? ' (' + detail + ')' : ''));
  if (!ok) process.exitCode = 1;
}

(async () => {

  // ---- Scenario A: Low pretest, PERC all-negative -> ruled out without D-dimer
  await withPage(async (page) => {
    await goHome(page);
    await checkRespItems(page, []); // no respiratory points
    await fillVitals(page, { hr: 70, sbp: 120, raSpo2: 99 });
    await checkAssocItems(page, []); // no DVT signs, no fever, etc.
    await checkRiskItems(page, []);
    await pickAltDx(page, 'asLikely'); // alternative dx at least as likely -> pushes toward low/atypical
    await seeResults(page);

    const tag = await page.textContent('#result-tag-text');
    log('Scenario A: pretest classified Low', tag === 'Low probability', 'got "' + tag + '"');

    await page.click('#btn-next-step'); // -> perc screen
    await page.fill('#f-age', '30'); // young -> negative age item

    const score = await page.textContent('#perc-score-pill');
    log('Scenario A: PERC score is 0/8', score.trim() === '0 / 8', 'got "' + score + '"');

    const btnText = await page.textContent('#btn-perc-continue');
    log('Scenario A: continue button offers PE-excluded result', /PE Excluded/.test(btnText), 'got "' + btnText + '"');

    await page.click('#btn-perc-continue'); // -> final (perc)
    const title = await page.textContent('#outcome-title');
    log('Scenario A: final screen shows PERC-negative rule-out', title === 'PE Ruled Out — PERC Negative', 'got "' + title + '"');
    const cite = await page.textContent('#outcome-cite');
    log('Scenario A: cites PROPER JAMA 2018', /JAMA\. 2018;319\(6\):559/.test(cite));
  });

  // ---- Scenario B: Low pretest, PERC positive (age 55) -> falls through to D-dimer <1000
  await withPage(async (page) => {
    await goHome(page);
    await checkRespItems(page, []);
    await fillVitals(page, { hr: 70, sbp: 120, raSpo2: 99 });
    await checkAssocItems(page, []);
    await checkRiskItems(page, []);
    await pickAltDx(page, 'asLikely');
    await seeResults(page);
    await page.click('#btn-next-step'); // -> perc
    await page.fill('#f-age', '55'); // >=50 -> PERC positive

    const score = await page.textContent('#perc-score-pill');
    log('Scenario B: PERC score is 1/8', score.trim() === '1 / 8', 'got "' + score + '"');

    const btnText = await page.textContent('#btn-perc-continue');
    log('Scenario B: continue button routes to D-dimer', /Continue to D-dimer/.test(btnText), 'got "' + btnText + '"');

    await page.click('#btn-perc-continue'); // -> ddimer
    const val = await page.textContent('#ddimer-threshold-value');
    log('Scenario B: D-dimer threshold is 1000', val.replace(/\s/g, '') === '<1000ng/mL', 'got "' + val + '"');
    const pretext = await page.textContent('#ddimer-pretext');
    log('Scenario B: pretext flags PERC-positive', /PERC-POSITIVE/.test(pretext), 'got "' + pretext + '"');
  });

  // ---- Scenario C: Moderate pretest, 0 YEARS items -> D-dimer threshold 1000
  await withPage(async (page) => {
    await goHome(page);
    await checkRespItems(page, ['syncope']); // severity criterion
    await fillVitals(page, { hr: 70, sbp: 120, raSpo2: 99 });
    await checkAssocItems(page, []); // no signs of DVT
    await checkRiskItems(page, []);
    await pickAltDx(page, 'asLikely'); // severe + asLikely -> moderate; PE-most-likely item = false
    await seeResults(page);

    const tag = await page.textContent('#result-tag-text');
    log('Scenario C: pretest classified Moderate', tag === 'Moderate probability', 'got "' + tag + '"');

    await page.click('#btn-next-step'); // -> ddimer directly (moderate skips PERC)
    const active = await page.getAttribute('.screen.active', 'data-screen');
    log('Scenario C: moderate routes straight to D-dimer (no PERC)', active === 'ddimer', 'got "' + active + '"');

    const val = await page.textContent('#ddimer-threshold-value');
    log('Scenario C: 0 YEARS items -> threshold 1000', val.replace(/\s/g, '') === '<1000ng/mL', 'got "' + val + '"');
    const pretext = await page.textContent('#ddimer-pretext');
    log('Scenario C: pretext shows YEARS 0/3', /YEARS 0\/3/.test(pretext), 'got "' + pretext + '"');
  });

  // ---- Scenario D: Moderate pretest, 1 YEARS item (hemoptysis) -> threshold 500
  await withPage(async (page) => {
    await goHome(page);
    await checkRespItems(page, ['syncope', 'hemoptysis']);
    await fillVitals(page, { hr: 70, sbp: 120, raSpo2: 99 });
    await checkAssocItems(page, []);
    await checkRiskItems(page, []);
    await pickAltDx(page, 'asLikely');
    await seeResults(page);

    const tag = await page.textContent('#result-tag-text');
    log('Scenario D: pretest still classified Moderate', tag === 'Moderate probability', 'got "' + tag + '"');

    await page.click('#btn-next-step');
    const val = await page.textContent('#ddimer-threshold-value');
    log('Scenario D: 1 YEARS item (hemoptysis) -> threshold 500', val.replace(/\s/g, '') === '<500ng/mL', 'got "' + val + '"');
    const pretext = await page.textContent('#ddimer-pretext');
    log('Scenario D: pretext shows YEARS 1/3', /YEARS 1\/3/.test(pretext), 'got "' + pretext + '"');

    // finish the D-dimer flow to confirm final screen cites YEARS
    await page.fill('#f-ddimer', '300');
    await page.click('#btn-interpret');
    const title = await page.textContent('#outcome-title');
    log('Scenario D: D-dimer 300 < 500 -> PE ruled out', title === 'PE Ruled Out', 'got "' + title + '"');
    const cite = await page.textContent('#outcome-cite');
    log('Scenario D: final cite references YEARS Lancet 2017', /Lancet\. 2017;390\(10091\):289/.test(cite));
  });

  // ---- Scenario E: High pretest unaffected (still skips PERC/D-dimer entirely)
  await withPage(async (page) => {
    await goHome(page);
    await checkRespItems(page, ['syncope']);
    await fillVitals(page, { hr: 70, sbp: 120, raSpo2: 99 });
    await checkAssocItems(page, []);
    await checkRiskItems(page, []);
    await pickAltDx(page, 'lessLikely'); // severe + lessLikely -> high
    await seeResults(page);
    const tag = await page.textContent('#result-tag-text');
    log('Scenario E: pretest classified High', tag === 'High probability', 'got "' + tag + '"');
    await page.click('#btn-next-step');
    const active = await page.getAttribute('.screen.active', 'data-screen');
    log('Scenario E: high routes straight to imaging final screen', active === 'final', 'got "' + active + '"');
    const title = await page.textContent('#outcome-title');
    log('Scenario E: imaging indicated title shown', title === 'Imaging Indicated', 'got "' + title + '"');
  });

  console.log(process.exitCode ? '\nSOME TESTS FAILED' : '\nALL TESTS PASSED');
})();
