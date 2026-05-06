/**
 * Live walkthrough screenshot script (CommonJS).
 * Drives the full golden-path workflow with real data and captures 7 screenshots.
 */

const { chromium } = require('/tmp/pw-runner/node_modules/playwright');
const path = require('path');

const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');
const SAMPLE_PARQUET = path.join(__dirname, '..', 'sample_data', 'sample.parquet');
const BASE_URL = 'http://localhost:5173';

async function shot(page, name, label) {
  const out = path.join(SCREENSHOTS_DIR, name);
  await page.screenshot({ path: out, fullPage: false });
  console.log(`  ✓ ${label}`);
  console.log(`    → ${name}`);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await ctx.newPage();

  // ── 1. Landing page ──
  console.log('\nStep 1: Landing page');
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await shot(page, '01-landing.png', 'Landing page — hero, upload card, feature tiles');

  // ── 2. File selected, columns configured ──
  console.log('\nStep 2: File + column config');
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(SAMPLE_PARQUET);
  await page.waitForTimeout(500);
  const colInput = page.locator('#columns-input');
  await colInput.fill('user_id, region, event_type');
  await page.waitForTimeout(300);
  await shot(page, '02-configured.png', 'File loaded (sample.parquet), columns + workers configured');

  // ── 3. Submit and wait for results ──
  console.log('\nStep 3: Submitting analysis…');
  await page.locator('.analyze-btn').click();
  await page.waitForSelector('.metrics-grid', { timeout: 25000 });
  await page.waitForTimeout(1200); // let D3 bar chart animate

  // ── 4. Results — user_id (high skew) ──
  console.log('\nStep 4: Results — user_id column (9.2× skew)');
  await page.locator('.results-main').evaluate(el => el.scrollTo(0, 0));
  await page.waitForTimeout(300);
  await shot(page, '03-results-user-id.png', 'Results: user_id — 9.2× skew ratio, top-key distribution chart');

  // ── 5. Straggler timeline ──
  console.log('\nStep 5: Straggler timeline');
  await page.locator('.timeline-wrap').scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  await shot(page, '04-straggler-timeline.png', 'Straggler timeline — 3.69× slowdown, 8 workers, 73% idle');

  // ── 6. Switch to region column (low skew) ──
  console.log('\nStep 6: region column (healthy)');
  const regionTab = page.locator('.col-tab', { hasText: 'region' });
  await regionTab.click();
  await page.waitForTimeout(700);
  await page.locator('.results-main').evaluate(el => el.scrollTo(0, 0));
  await page.waitForTimeout(400);
  await shot(page, '05-results-region.png', 'Results: region — low skew (2.1×), uniform distribution');

  // ── 7. Advisor panel — DuckDB salting ──
  console.log('\nStep 7: Advisor — DuckDB salting SQL');
  const userIdRow = page.locator('.score-row').first();
  await userIdRow.click();
  await page.waitForTimeout(300);
  const saltingBtn = page.locator('.toggle-btn', { hasText: 'Salting' });
  await saltingBtn.first().click();
  await page.waitForTimeout(200);
  await page.locator('.advisor-wrap').scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  await shot(page, '06-advisor-duckdb-salting.png', 'Advisor: ready-to-paste DuckDB salting SQL for user_id');

  // ── 8. PySpark repartition ──
  console.log('\nStep 8: Advisor — PySpark repartition');
  const pysparkBtn = page.locator('.toggle-btn', { hasText: 'PySpark' });
  await pysparkBtn.click();
  await page.waitForTimeout(200);
  const repartBtn = page.locator('.toggle-btn', { hasText: 'Repartition' });
  await repartBtn.click();
  await page.waitForTimeout(300);
  await shot(page, '07-advisor-pyspark-repartition.png', 'Advisor: PySpark repartition snippet');

  await browser.close();

  console.log('\n✓ All 7 screenshots saved to docs/screenshots/');
})().catch(err => {
  console.error('Screenshot script failed:', err);
  process.exit(1);
});
