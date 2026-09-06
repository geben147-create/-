// STEP 7 — 검수. Drives the real page in a real browser at the widths the
// guide lists, and reports what it finds instead of trusting the CSS.
// STEP 7 harness. Run it, don't eyeball it.
//   python3 -m http.server 8811 --directory site &
//   npm i playwright-core && node pipeline/qa.js /tmp/qa
// Set CHROME=/path/to/chrome if playwright can't find a browser.
const { chromium } = require('playwright-core');

const WIDTHS = [1920, 1440, 1024, 768, 390, 360];
const SHORT  = { w: 1440, h: 580 };   // laptop + bookmarks bar + extensions
const URL    = 'http://127.0.0.1:8811/';
const OUT    = process.argv[2] || '/tmp/qa';

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined });
  const problems = [];

  for (const w of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    const errs = [];
    page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
    page.on('pageerror', e => errs.push('pageerror: ' + e.message));

    await page.addInitScript(() => {
      // smooth scrolling makes screenshots land mid-animation
      const st = document.createElement('style');
      st.textContent = 'html{scroll-behavior:auto !important}';
      document.addEventListener('DOMContentLoaded', () => document.head.appendChild(st));
    });
    await page.goto(URL, { waitUntil: 'load' });
    await page.waitForTimeout(500);

    // the page must never scroll sideways
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth - document.documentElement.clientWidth);

    // the layer contract: nothing may outrank the copy inside a stage
    const layers = await page.evaluate(() => {
      const bad = [];
      document.querySelectorAll('.stage').forEach(st => {
        if (getComputedStyle(st).isolation !== 'isolate')
          bad.push('.stage without isolation:isolate');
        const z = el => el ? getComputedStyle(el).zIndex : null;
        const v = z(st.querySelector('.stage__bg'));
        const s = z(st.querySelector('.stage__scrim'));
        const c = z(st.querySelector('.stage__copy'));
        if (!(Number(v) < Number(s) && Number(s) < Number(c)))
          bad.push(`${st.id || '(stage)'} layer order video:${v} scrim:${s} copy:${c}`);
      });
      // and no ancestor of a stage may create its own context
      document.querySelectorAll('.stage').forEach(st => {
        for (let p = st.parentElement; p && p !== document.documentElement; p = p.parentElement) {
          const cs = getComputedStyle(p);
          if (cs.transform !== 'none' || cs.filter !== 'none' ||
              Number(cs.opacity) < 1 || cs.willChange !== 'auto')
            bad.push(`ancestor <${p.tagName.toLowerCase()}> of #${st.id} breaks the context`);
        }
      });
      return bad;
    });

    // every video must carry the four attributes iOS needs
    const attrs = await page.evaluate(() => {
      const bad = [];
      document.querySelectorAll('video').forEach(v => {
        ['muted', 'playsinline'].forEach(a => {
          if (!v.hasAttribute(a)) bad.push(`${v.dataset.clip}: missing ${a}`);
        });
        if (!v.hasAttribute('poster')) bad.push(`${v.dataset.clip}: no poster`);
      });
      return bad;
    });

    // does the scrub section actually pin?
    let pinned = null;
    if (w >= 768) {
      await page.evaluate(() => document.getElementById('scrubWrap')
        .scrollIntoView({ block: 'start', behavior: 'instant' }));
      await page.waitForTimeout(200);
      const a = await page.evaluate(() =>
        document.getElementById('safezone').getBoundingClientRect().top);
      await page.evaluate(() => window.scrollBy(0, 600));
      await page.waitForTimeout(200);
      const b = await page.evaluate(() =>
        document.getElementById('safezone').getBoundingClientRect().top);
      const bar = await page.evaluate(() =>
        document.getElementById('scrubBar').style.width);
      pinned = { stayedPut: Math.abs(a - b) < 2, a: Math.round(a), b: Math.round(b), bar };
      if (!pinned.stayedPut) problems.push(`${w}px: scrub section did not pin (${a} -> ${b})`);
      if (!bar || bar === '0%') problems.push(`${w}px: scrub progress bar never advanced`);
    }

    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${OUT}/hero-${w}.png` });
    await page.evaluate(() => document.getElementById('type').scrollIntoView());
    await page.waitForTimeout(250);
    await page.screenshot({ path: `${OUT}/type-${w}.png` });

    if (overflow > 0) problems.push(`${w}px: page scrolls sideways by ${overflow}px`);
    layers.forEach(l => problems.push(`${w}px: ${l}`));
    attrs.forEach(a => problems.push(`${w}px: ${a}`));
    // media 404s are expected here — the CDN is blocked from this container
    const real = errs.filter(e => !/videocdn\.pollo\.ai|ERR_|Failed to load|net::/i.test(e));
    real.forEach(e => problems.push(`${w}px console: ${e}`));

    console.log(`${String(w).padStart(4)}px  overflow=${overflow}  layers=${layers.length}` +
      `  attrs=${attrs.length}  console=${real.length}` +
      (pinned ? `  pin=${pinned.stayedPut ? 'ok' : 'BROKEN'} bar=${pinned.bar}` : ''));
    await ctx.close();
  }

  // the short-window case the guide says everyone forgets
  const ctx = await browser.newContext({ viewport: { width: SHORT.w, height: SHORT.h } });
  const page = await ctx.newPage();
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(400);
  const clipped = await page.evaluate(() => {
    const c = document.querySelector('.hero__copy').getBoundingClientRect();
    return { bottom: Math.round(c.bottom), vh: window.innerHeight, cut: c.bottom > window.innerHeight };
  });
  await page.screenshot({ path: `${OUT}/hero-short-${SHORT.w}x${SHORT.h}.png` });
  console.log(`short window ${SHORT.w}x${SHORT.h}: hero copy bottom=${clipped.bottom} vh=${clipped.vh}` +
    (clipped.cut ? '  CLIPPED' : '  fits'));
  if (clipped.cut) problems.push(`short window ${SHORT.w}x${SHORT.h}: hero copy is clipped`);
  await ctx.close();

  // reduced motion must kill every video
  const rm = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const rp = await rm.newPage();
  await rp.goto(URL, { waitUntil: 'load' });
  await rp.waitForTimeout(400);
  const still = await rp.evaluate(() => {
    const vids = [...document.querySelectorAll('video')];
    return {
      hidden: vids.every(v => getComputedStyle(v).display === 'none'),
      wired: vids.some(v => v.querySelector('source')),
      posters: [...document.querySelectorAll('.stage__poster')]
                 .every(p => getComputedStyle(p).display !== 'none'),
    };
  });
  await rp.screenshot({ path: `${OUT}/reduced-motion.png` });
  console.log(`reduced-motion: videos hidden=${still.hidden} sources attached=${still.wired} stills shown=${still.posters}`);
  if (!still.hidden) problems.push('reduced motion: videos are still displayed');
  if (still.wired)   problems.push('reduced motion: video sources were still attached (wasted bytes)');
  await rm.close();

  await browser.close();
  console.log('\n' + (problems.length ? 'PROBLEMS:\n - ' + problems.join('\n - ') : 'no problems found'));
  process.exit(problems.length ? 1 : 0);
})();
