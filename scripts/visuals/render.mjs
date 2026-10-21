// Render the visuals in docs/visuals/ to PDF and PNG with headless Chromium.
// Setup once: npm i playwright && npx playwright install chromium
// Usage: node scripts/visuals/render.mjs
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, unlinkSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, '..', '..', 'docs', 'visuals');
const browser = await chromium.launch();

async function render(file, { pdf, width, height }) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 2 });
  await page.goto(pathToFileURL(file).href, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  const base = file.replace(/\.html$/, '');
  if (pdf) await page.pdf({ path: `${base}.pdf`, preferCSSPageSize: true, printBackground: true });
  await page.screenshot({ path: `${base}.png`, fullPage: true });
  await page.close();
}

for (const rig of ['rig1', 'rig2']) await render(join(out, `${rig}.html`), { pdf: true, width: 816, height: 1056 });

// The pipeline page is published as an Artifact, which adds the doctype and charset; add them for the local render.
const tmp = join(out, 'pipeline.render.html');
writeFileSync(tmp, '<!doctype html><meta charset="utf-8">\n' + readFileSync(join(here, 'pipeline.html'), 'utf8'));
await render(tmp, { pdf: false, width: 1560, height: 1000 });
writeFileSync(join(out, 'pipeline.png'), readFileSync(join(out, 'pipeline.render.png')));
unlinkSync(tmp); unlinkSync(join(out, 'pipeline.render.png'));
await browser.close();
