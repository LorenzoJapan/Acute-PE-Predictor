const { chromium } = require('playwright');
const path = require('path');

function assert(cond, msg) {
  if (!cond) throw new Error('ASSERTION FAILED: ' + msg);
  console.log('  ok - ' + msg);
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const consoleErrors = [];
  page.on('pageerror', (err) => consoleErrors.push(err.message));
  page.on('console', (msg) => { if (msg.type() === 'error' && !msg.text().includes('ERR_TUNNEL') && !msg.text().includes('net::')) consoleErrors.push(msg.text()); });

  const url = 'file://' + path.resolve(__dirname, '..', 'index.html');

  async function reload() {
    await page.goto(url);
    await page.waitForSelector('#scr-home.active');
  }

  // ================= CLINICAL GESTALT PATHWAY =================

  // ---------- Test 1: Gestalt -> Low -> PERC all-negative -> PE excluded ----------
  console.log('\nTest 1: Gestalt, Low, PERC negative (all 8 negative)');
  await reload();
  await page.click('[data-go="gw-gestalt"]');
  await page.waitForSelector('#scr-gw-gestalt.active');
  await page.click('.tier-card.tier-low');
  await page.waitForSelector('#scr-gw-result.active');
  const tag1 = await page.textContent('#gw-result-tag-text');
  assert(tag1.trim() === 'Low probability', 'result tag shows Low probability, got "' + tag1 + '"');
  await page.click('#gw-btn-next-step');
  await page.waitForSelector('#scr-gw-perc.active');
  await page.fill('#f-gw-age', '30');
  // leave all checkboxes unchecked -> PERC score 0
  const percPill1 = await page.textContent('#gw-perc-score-pill');
  assert(percPill1.trim() === '0 / 8', 'PERC score is 0/8, got "' + percPill1 + '"');
  const contBtnText1 = await page.textContent('#gw-btn-perc-continue');
  assert(contBtnText1.includes('PE Excluded'), 'continue button offers "PE Excluded" path, got "' + contBtnText1 + '"');
  await page.click('#gw-btn-perc-continue');
  await page.waitForSelector('#scr-gw-final.active');
  const title1 = await page.textContent('#gw-outcome-title');
  assert(title1.trim() === 'PE Ruled Out — PERC Negative', 'final title is PERC-negative rule-out, got "' + title1 + '"');

  // ---------- Test 2: Gestalt -> Low -> PERC positive -> YEARS 0/3 -> threshold 1000 -> ruled out ----------
  // Per Figure 1 of the 2026 AHA/ACC PE guideline, a PERC-positive low-probability
  // patient feeds into the SAME D-dimer + YEARS assessment box as intermediate
  // probability, not a separate fixed <1000 ng/mL rule.
  console.log('\nTest 2: Gestalt, Low, PERC positive, YEARS 0/3 -> threshold 1000, D-dimer 400 -> ruled out');
  await reload();
  await page.click('[data-go="gw-gestalt"]');
  await page.click('.tier-card.tier-low');
  await page.waitForSelector('#scr-gw-result.active');
  await page.click('#gw-btn-next-step');
  await page.waitForSelector('#scr-gw-perc.active');
  await page.fill('#f-gw-age', '55'); // age >=50 -> +1 point, PERC positive
  const percPill2 = await page.textContent('#gw-perc-score-pill');
  assert(percPill2.trim() === '1 / 8', 'PERC score is 1/8 (age>=50), got "' + percPill2 + '"');
  const contBtnText2 = await page.textContent('#gw-btn-perc-continue');
  assert(contBtnText2.includes('D-dimer'), 'continue button routes to D-dimer, got "' + contBtnText2 + '"');
  await page.click('#gw-btn-perc-continue');
  await page.waitForSelector('#scr-gw-ddimer.active');
  const yearsCardVisible2 = await page.isVisible('#gw-years-card');
  assert(yearsCardVisible2 === true, 'YEARS card is shown for low/PERC-positive (per Figure 1, shares the intermediate D-dimer+YEARS box)');
  const yearsCheckboxCount2 = await page.locator('#gw-years-list input[type="checkbox"]').count();
  assert(yearsCheckboxCount2 === 3, 'YEARS list is interactive for low/PERC-positive, 3 checkboxes, got ' + yearsCheckboxCount2);
  const thresholdVal2 = await page.textContent('#gw-ddimer-threshold-value');
  assert(thresholdVal2.includes('1000'), 'threshold is <1000 with 0 YEARS items, got "' + thresholdVal2 + '"');
  await page.fill('#f-gw-ddimer', '400');
  await page.click('#gw-btn-interpret');
  await page.waitForSelector('#scr-gw-final.active');
  const title2 = await page.textContent('#gw-outcome-title');
  assert(title2.trim() === 'PE Ruled Out', 'final title is PE Ruled Out, got "' + title2 + '"');

  // ---------- Test 2b: Gestalt -> Low -> PERC positive -> YEARS >=1 -> threshold 500 -> imaging ----------
  console.log('\nTest 2b: Gestalt, Low, PERC positive, YEARS 1/3 (hemoptysis) -> threshold 500, D-dimer 600 -> imaging');
  await reload();
  await page.click('[data-go="gw-gestalt"]');
  await page.click('.tier-card.tier-low');
  await page.waitForSelector('#scr-gw-result.active');
  await page.click('#gw-btn-next-step');
  await page.waitForSelector('#scr-gw-perc.active');
  await page.fill('#f-gw-age', '30');
  await page.click('#gw-perc-fresh-list [data-key="hemoptysis"]');
  await page.click('#gw-btn-perc-continue');
  await page.waitForSelector('#scr-gw-ddimer.active');
  await page.click('#gw-years-list [data-key="hemoptysis"]');
  const thresholdVal2b = await page.textContent('#gw-ddimer-threshold-value');
  assert(thresholdVal2b.includes('500'), 'threshold is <500 with 1 YEARS item present, got "' + thresholdVal2b + '"');
  await page.fill('#f-gw-ddimer', '600');
  await page.click('#gw-btn-interpret');
  await page.waitForSelector('#scr-gw-final.active');
  const title2b = await page.textContent('#gw-outcome-title');
  assert(title2b.trim() === 'Imaging Indicated', 'final title is Imaging Indicated (600 >= 500 threshold), got "' + title2b + '"');

  // ---------- Test 3: Gestalt -> Intermediate -> fresh YEARS checklist, 0 items -> threshold 1000 ----------
  console.log('\nTest 3: Gestalt Intermediate, fresh YEARS checklist (0 items) -> threshold 1000, ddimer 300 -> ruled out');
  await reload();
  await page.click('[data-go="gw-gestalt"]');
  await page.click('.tier-card.tier-intermediate');
  await page.waitForSelector('#scr-gw-result.active');
  const tag3 = await page.textContent('#gw-result-tag-text');
  assert(tag3.trim() === 'Intermediate probability', 'result tag shows Intermediate probability, got "' + tag3 + '"');
  await page.click('#gw-btn-next-step');
  await page.waitForSelector('#scr-gw-ddimer.active');
  const yearsCheckboxCount3 = await page.locator('#gw-years-list input[type="checkbox"]').count();
  assert(yearsCheckboxCount3 === 3, 'YEARS list is interactive, 3 checkboxes, got ' + yearsCheckboxCount3);
  const thresholdVal3 = await page.textContent('#gw-ddimer-threshold-value');
  assert(thresholdVal3.includes('1000'), 'threshold is <1000 (0 YEARS items), got "' + thresholdVal3 + '"');
  await page.fill('#f-gw-ddimer', '300');
  await page.click('#gw-btn-interpret');
  await page.waitForSelector('#scr-gw-final.active');
  const title3 = await page.textContent('#gw-outcome-title');
  assert(title3.trim() === 'PE Ruled Out', 'final title is PE Ruled Out, got "' + title3 + '"');

  // ---------- Test 4: Gestalt -> High -> unstable -> bedside TTE alert ----------
  console.log('\nTest 4: Gestalt High, unstable (shock criteria met) -> bedside TTE');
  await reload();
  await page.click('[data-go="gw-gestalt"]');
  await page.click('.tier-card.tier-high');
  await page.waitForSelector('#scr-gw-result.active');
  const tag4 = await page.textContent('#gw-result-tag-text');
  assert(tag4.trim() === 'High probability', 'result tag shows High probability, got "' + tag4 + '"');
  await page.click('#gw-btn-next-step');
  await page.waitForSelector('#scr-gw-instability.active');
  await page.fill('#f-gw-sbp', '80');
  await page.fill('#f-gw-hr', '130'); // tachycardic -> shock criteria met (SBP<90 + tachy)
  const shockPill4 = await page.textContent('#gw-shock-pill');
  assert(shockPill4.trim() === 'MET', 'shock criteria met (SBP<90 + HR>100), got "' + shockPill4 + '"');
  await page.click('#gw-btn-instability-continue');
  await page.waitForSelector('#scr-gw-final.active');
  const title4 = await page.textContent('#gw-outcome-title');
  assert(title4.trim() === 'Unstable — Consider Bedside TTE', 'final title flags bedside TTE, got "' + title4 + '"');
  const alertVisible4 = await page.isVisible('#gw-outcome-alert');
  assert(alertVisible4 === true, 'critical alert box is visible');

  // ---------- Test 5: Gestalt -> High -> stable -> Imaging Indicated ----------
  console.log('\nTest 5: Gestalt High, stable -> Imaging Indicated');
  await reload();
  await page.click('[data-go="gw-gestalt"]');
  await page.click('.tier-card.tier-high');
  await page.waitForSelector('#scr-gw-result.active');
  await page.click('#gw-btn-next-step');
  await page.waitForSelector('#scr-gw-instability.active');
  await page.fill('#f-gw-sbp', '120');
  await page.fill('#f-gw-hr', '110');
  const shockPill5 = await page.textContent('#gw-shock-pill');
  assert(shockPill5.trim() === 'NOT MET', 'shock criteria not met (SBP normal), got "' + shockPill5 + '"');
  await page.click('#gw-btn-instability-continue');
  await page.waitForSelector('#scr-gw-final.active');
  const title5 = await page.textContent('#gw-outcome-title');
  assert(title5.trim() === 'Imaging Indicated', 'final title is Imaging Indicated, got "' + title5 + '"');

  // ---------- Test 6: Copy summary works and New Assessment resets gw state ----------
  console.log('\nTest 6: Copy summary works and New Assessment resets gw state');
  await page.click('#gw-btn-copy');
  await page.waitForSelector('#gw-toast.show');
  const toastText6 = await page.textContent('#gw-toast');
  assert(toastText6.trim() === 'Summary copied' || toastText6.trim() === 'Copy unavailable', 'copy summary toast fired, got "' + toastText6 + '"');
  await page.click('#gw-btn-restart');
  await page.waitForSelector('#scr-home.active');
  // Navigate back into gestalt pathway (High, from Test 5's stable run) and confirm
  // the instability vitals were cleared rather than carried over from the prior run.
  await page.click('[data-go="gw-gestalt"]');
  await page.waitForSelector('#scr-gw-gestalt.active');
  await page.click('.tier-card.tier-high');
  await page.waitForSelector('#scr-gw-result.active');
  await page.click('#gw-btn-next-step');
  await page.waitForSelector('#scr-gw-instability.active');
  const sbpAfterRestart = await page.inputValue('#f-gw-sbp');
  const hrAfterRestart = await page.inputValue('#f-gw-hr');
  assert(sbpAfterRestart === '' && hrAfterRestart === '', 'instability vitals cleared after New Assessment, got sbp="' + sbpAfterRestart + '" hr="' + hrAfterRestart + '"');

  // ================= WELLS EXPANDED PATHWAY (original structured assessment) =================

  // ---------- Test 7: Wells Expanded -> Low (atypical, alt dx as likely) -> PERC negative -> PE excluded ----------
  console.log('\nTest 7: Wells Expanded Criteria Pathway, Low, PERC negative -> PE Ruled Out');
  await reload();
  await page.click('[data-go="resp"]');
  await page.waitForSelector('#scr-resp.active');
  // leave all respiratory symptom checkboxes unchecked
  await page.click('[data-go="assoc"]');
  await page.waitForSelector('#scr-assoc.active');
  await page.fill('#f-sbp', '120');
  await page.fill('#f-hr', '80');
  await page.fill('#f-raSpo2', '98');
  const contBtn7 = page.locator('#btn-continue-assoc');
  await contBtn7.click();
  await page.waitForSelector('#scr-judgment.active');
  await page.click('#seg-altdx [data-val="asLikely"]');
  await page.click('#btn-see-results');
  await page.waitForSelector('#scr-results.active');
  const tag7 = await page.textContent('#result-tag-text');
  assert(tag7.trim() === 'Low probability', 'result tag shows Low probability, got "' + tag7 + '"');
  await page.click('#btn-next-step');
  await page.waitForSelector('#scr-perc.active');
  await page.fill('#f-age', '30');
  const percPill7 = await page.textContent('#perc-score-pill');
  assert(percPill7.trim() === '0 / 8', 'PERC score is 0/8, got "' + percPill7 + '"');
  await page.click('#btn-perc-continue');
  await page.waitForSelector('#scr-final.active');
  const title7 = await page.textContent('#outcome-title');
  assert(title7.trim() === 'PE Ruled Out — PERC Negative', 'final title is PERC-negative rule-out, got "' + title7 + '"');

  // ---------- Test 7b: Wells Expanded -> Low, PERC positive -> YEARS carried over (hemoptysis) -> threshold 500 -> imaging ----------
  // Per Figure 1 of the 2026 AHA/ACC PE guideline, a PERC-positive low-probability
  // patient shares the same D-dimer + YEARS assessment box as intermediate probability.
  console.log('\nTest 7b: Wells Expanded Pathway, Low, PERC positive, YEARS 1/3 (hemoptysis carried) -> threshold 500, imaging');
  await reload();
  await page.click('[data-go="resp"]');
  await page.waitForSelector('#scr-resp.active');
  await page.click('#resp-list [data-key="hemoptysis"]'); // also a YEARS item, carried over
  await page.click('[data-go="assoc"]');
  await page.waitForSelector('#scr-assoc.active');
  await page.fill('#f-sbp', '120');
  await page.fill('#f-hr', '80');
  await page.fill('#f-raSpo2', '98');
  await page.click('#btn-continue-assoc');
  await page.waitForSelector('#scr-judgment.active');
  await page.click('#seg-altdx [data-val="asLikely"]');
  await page.click('#btn-see-results');
  await page.waitForSelector('#scr-results.active');
  const tag7b = await page.textContent('#result-tag-text');
  assert(tag7b.trim() === 'Low probability', 'result tag shows Low probability, got "' + tag7b + '"');
  await page.click('#btn-next-step');
  await page.waitForSelector('#scr-perc.active');
  await page.fill('#f-age', '30');
  const percPill7b = await page.textContent('#perc-score-pill');
  assert(percPill7b.trim() !== '0 / 8', 'PERC is positive (hemoptysis carried over), got "' + percPill7b + '"');
  await page.click('#btn-perc-continue');
  await page.waitForSelector('#scr-ddimer.active');
  const yearsCardVisible7b = await page.isVisible('#years-card');
  assert(yearsCardVisible7b === true, 'YEARS card is shown for low/PERC-positive (per Figure 1)');
  const thresholdVal7b = await page.textContent('#ddimer-threshold-value');
  assert(thresholdVal7b.includes('500'), 'threshold is <500 with 1 YEARS item (hemoptysis) present, got "' + thresholdVal7b + '"');
  await page.fill('#f-ddimer', '600');
  await page.click('#btn-interpret');
  await page.waitForSelector('#scr-final.active');
  const title7b = await page.textContent('#outcome-title');
  assert(title7b.trim() === 'Imaging Indicated', 'final title is Imaging Indicated (600 >= 500 threshold), got "' + title7b + '"');

  // ---------- Test 8: Wells Expanded -> High (severe, alt dx less likely) -> stable -> Imaging Indicated ----------
  console.log('\nTest 8: Wells Expanded Criteria Pathway, High (syncope, severe), stable -> Imaging Indicated');
  await reload();
  await page.click('[data-go="resp"]');
  await page.waitForSelector('#scr-resp.active');
  await page.click('#resp-list [data-key="syncope"]');
  await page.click('[data-go="assoc"]');
  await page.waitForSelector('#scr-assoc.active');
  await page.fill('#f-sbp', '120');
  await page.fill('#f-hr', '85');
  await page.fill('#f-raSpo2', '97');
  await page.click('#btn-continue-assoc');
  await page.waitForSelector('#scr-judgment.active');
  await page.click('#seg-altdx [data-val="lessLikely"]');
  await page.click('#btn-see-results');
  await page.waitForSelector('#scr-results.active');
  const tag8 = await page.textContent('#result-tag-text');
  assert(tag8.trim() === 'High probability', 'result tag shows High probability, got "' + tag8 + '"');
  const nextBtnText8 = await page.textContent('#btn-next-step');
  assert(nextBtnText8.includes('Imaging'), 'continue button routes straight to imaging (no separate instability screen), got "' + nextBtnText8 + '"');
  await page.click('#btn-next-step');
  await page.waitForSelector('#scr-final.active');
  const title8 = await page.textContent('#outcome-title');
  assert(title8.trim() === 'Imaging Indicated', 'final title is Imaging Indicated, got "' + title8 + '"');

  // ---------- Test 9: Home screen wires both pathways correctly; no orphaned Wells-checklist screen ----------
  console.log('\nTest 9: Home screen entry points and no orphaned gw-wells screen');
  await reload();
  const wellsEntry = await page.locator('#scr-home [data-go="resp"]').count();
  assert(wellsEntry === 1, 'home screen links Wells Expanded Criteria Pathway to the original structured assessment, got ' + wellsEntry);
  const gestaltEntry = await page.locator('#scr-home [data-go="gw-gestalt"]').count();
  assert(gestaltEntry === 1, 'home screen links Clinical Gestalt Pathway, got ' + gestaltEntry);
  const orphanedWellsScreen = await page.locator('#scr-gw-wells').count();
  assert(orphanedWellsScreen === 0, 'the old single-page Wells checklist screen no longer exists, got ' + orphanedWellsScreen);
  const structuredScreensPresent = await page.locator('#scr-resp, #scr-assoc, #scr-judgment, #scr-results, #scr-perc, #scr-ddimer, #scr-final').count();
  assert(structuredScreensPresent === 7, 'all 7 original structured-assessment screens exist in the DOM, got ' + structuredScreensPresent);

  console.log('\nConsole/page errors captured: ' + consoleErrors.length);
  if (consoleErrors.length) {
    consoleErrors.forEach(e => console.log('  ERROR: ' + e));
  }

  await browser.close();

  if (consoleErrors.length) {
    console.log('\nFAILED: console errors present');
    process.exit(1);
  }
  console.log('\nALL TESTS PASSED');
})().catch(e => {
  console.error('\nTEST FAILURE: ' + e.message);
  process.exit(1);
});
