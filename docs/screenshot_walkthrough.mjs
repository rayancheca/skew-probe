/**
 * Live walkthrough screenshot script.
 * Drives the full golden-path workflow with real data and captures 7 screenshots.
 * Run: node docs/screenshot_walkthrough.mjs
 */

import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');
const SAMPLE_PARQUET = path.join(__dirname, '..', 'sample_data', 'sample.parquet');
const BASE_URL = 'http://localhost:5173';

async function shot(page, name, label) {
  const out = path.join(SCREENSHOTS_DIR, name);
  await page.screenshot({ path: out, fullPage: false });
  console.log(`  ✓ ${label} → ${name}`);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await ctx.newPage();

  // ── 1. Landing page ──
  console.log('Step 1: Landing page');
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await shot(page, '01-landing.png', 'Landing page — upload form + feature cards');

  // ── 2. File selected, columns filled ──
  console.log('Step 2: File drop + column config');
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(SAMPLE_PARQUET);
  await page.waitForTimeout(400);

  const colInput = page.locator('#columns-input');
  await colInput.fill('user_id, region, event_type');

  // Set workers to 8 (already default, but drag for screenshot value)
  await page.locator('#workers-input').fill('8');
  await page.waitForTimeout(200);
  await shot(page, '02-file-configured.png', 'File loaded, columns configured, workers set');

  // ── 3. Submit and wait for results ──
  console.log('Step 3: Submitting — waiting for analysis…');
  await page.locator('.analyze-btn').click();
  // Wait for results to appear (skew metrics grid)
  await page.waitForSelector('.metrics-grid', { timeout: 20000 });
  await page.waitForTimeout(1000); // let D3 animations settle

  // ── 4. Full results view (user_id active) ──
  console.log('Step 4: Results — user_id column');
  await shot(page, '03-results-user-id.png', 'Results: user_id — 9.2× skew ratio, distribution chart');

  // ── 5. Scroll down to show straggler timeline ──
  console.log('Step 5: Straggler timeline');
  await page.locator('.timeline-wrap').scrollIntoViewIfNeeded();
  await page.waitForTimeout(700);
  await shot(page, '04-straggler-timeline.png', 'Straggler timeline — 3.69× slowdown, 73% idle workers');

  // ── 6. Switch to region column ──
  console.log('Step 6: Switch to region column');
  const regionTab = page.locator('.col-tab', { hasText: 'region' });
  await regionTab.click();
  await page.waitForTimeout(600);
  // Scroll back to top of results
  await page.locator('.results-main').evaluate(el => el.scrollTo(0, 0));
  await page.waitForTimeout(300);
  await shot(page, '05-results-region.png', 'Results: region column — low skew, healthy distribution');

  // ── 7. Advisor panel — DuckDB salting SQL ──
  console.log('Step 7: Advisor panel');
  // Click user_id row in advisor
  const advisorUserRow = page.locator('.score-row', { hasText: 'user_id' });
  await advisorUserRow.click();
  await page.waitForTimeout(300);
  // Make sure salting is selected
  const saltingBtn = page.locator('.toggle-btn', { hasText: 'Salting' });
  await saltingBtn.click();
  await page.waitForTimeout(200);
  await page.locator('.advisor-wrap').scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  await shot(page, '06-advisor-salting-sql.png', 'Advisor: DuckDB salting SQL for user_id hot key');

  // ── 8. PySpark repartition hint ──
  console.log('Step 8: PySpark repartition hint');
  const pysparkBtn = page.locator('.toggle-btn', { hasText: 'PySpark' });
  await pysparkBtn.click();
  const repartBtn = page.locator('.toggle-btn', { hasText: 'Repartition' });
  await repartBtn.click();
  await page.waitForTimeout(300);
  await shot(page, '07-advisor-pyspark.png', 'Advisor: PySpark repartition hint');

  await browser.close();
  console.log('\nAll 7 screenshots saved to docs/screenshots/');
})();
