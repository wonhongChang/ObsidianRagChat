// Run "npm run build" in frontend, then run with Playwright available to Node.
// Optional: set CHROMIUM_EXECUTABLE_PATH to an existing local Chrome binary.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const dist = path.resolve(__dirname, '../frontend/dist');
const out = path.resolve(__dirname, '../assets/screenshots');
const origin = 'http://readme-fixture.invalid';
const copy = {
  ko: { rec: '권장 5개', clear: '대화 초기화', cached: '캐시됨', count: '8개 노트 검색 가능' },
  en: { rec: 'Rec 5', clear: 'Clear', cached: 'Cached', count: '8 notes indexed' },
  ja: { rec: 'おすすめ 5件', clear: 'クリア', cached: 'キャッシュ', count: '8件のノートを検索可能' },
};

async function main() {
  assert(fs.existsSync(path.join(dist, 'index.html')), 'Build the frontend first.');
  const browser = await chromium.launch({
    headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined,
    args: ['--disable-background-networking'],
  });
  try {
    for (const [lang, words] of Object.entries(copy)) {
      const context = await browser.newContext({
        viewport: { width: 980, height: 870 }, deviceScaleFactor: 1,
        colorScheme: 'light', reducedMotion: 'reduce', locale: lang, serviceWorkers: 'block',
      });
      const failures = [];
      // Fulfil from the built frontend only; never forward to a server, vault, or model.
      await context.route('**/*', async route => {
        const url = new URL(route.request().url());
        if (url.origin === origin && route.request().method() === 'GET') {
          if (url.pathname === '/api/notes/count')
            return route.fulfill({ json: { success: true, count: 8 } });
          const name = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
          if (name === 'index.html' || name === 'favicon.svg' || /^assets\/[\w.-]+\.(?:js|css|svg)$/.test(name))
            return route.fulfill({ path: path.join(dist, name) });
        }
        failures.push('Unexpected network request');
        return route.abort('blockedbyclient');
      });
      const page = await context.newPage();
      page.on('pageerror', error => failures.push(error.message));
      for (const mode of ['', 'answer', 'tag', 'followup', 'cache']) {
        await page.setViewportSize({ width: 980, height: mode === 'tag' || mode === 'followup' ? 980 : 790 });
        await page.goto(origin + '/?lang=' + lang + (mode ? '&demo=' + mode : ''));
        await page.getByText(words.count, { exact: true }).waitFor();
        await page.getByText('GPT-6 Luna', { exact: true }).waitFor();
        await page.getByText(words.rec, { exact: true }).waitFor();
        assert.equal(await page.locator('select').inputValue(), lang);
        const sourceButtons = page.locator('button[aria-expanded]');
        assert.equal(await sourceButtons.count(), mode === 'followup' ? 2 : mode ? 1 : 0);
        if (mode) assert(await page.getByRole('button', { name: words.clear, exact: true }).isEnabled());
        if (mode === 'tag') {
          await sourceButtons.click();
          await page.getByText('00_Demo_Index.md', { exact: true }).waitFor();
          await page.mouse.move(0, 0);
        }
        if (mode === 'cache') await page.getByText(words.cached, { exact: true }).waitFor();
        await page.evaluate(() => document.fonts.ready);
        const layout = await page.evaluate(() => {
          const controls = Array.from(document.querySelectorAll('button, input, select, textarea'));
          return {
            horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
            clippedControls: controls.some(el => {
              const r = el.getBoundingClientRect();
              return r.width && (r.left < 0 || r.right > innerWidth + 1 || r.top < 0 || r.bottom > innerHeight + 1);
            }),
            clippedConversation: Array.from(document.querySelectorAll('.overflow-y-auto'))
              .some(el => el.scrollHeight > el.clientHeight + 1),
          };
        });
        assert.deepEqual(layout, { horizontalOverflow: false, clippedControls: false, clippedConversation: false }, lang + '/' + mode);
        assert.deepEqual(failures, []);
        const filename = 'demo-' + lang + (mode ? '-' + mode : '') + '.png';
        await page.screenshot({ path: path.join(out, filename), animations: 'disabled' });
        console.log(filename);
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
