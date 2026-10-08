// Records the README demo GIF: a short walk through the sandbox in practice mode.
//
//   python run_sandbox.py &                       # practice mode on :8000 / :4173
//   npm i --no-save playwright && npx playwright install chromium
//   node scripts/demo-gif.mjs                     # needs ffmpeg; writes assets/demo.gif
//
// Env: WEB_URL, API_URL, CHROME_CHANNEL (e.g. "chrome" to use an installed Chrome).

import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync } from "node:fs";

const WEB = process.env.WEB_URL || "http://localhost:4173";
const API = process.env.API_URL || "http://localhost:8000";
const OUT = new URL("../assets/", import.meta.url).pathname;
const FRAMES = `${OUT}.frames`;

rmSync(FRAMES, { recursive: true, force: true });
mkdirSync(FRAMES, { recursive: true });
await fetch(`${API}/_admin/reset`, { method: "POST" });
await fetch(`${WEB}/api/_admin/reset`, { method: "POST" });

const browser = await chromium.launch({ channel: process.env.CHROME_CHANNEL || undefined });
const page = await browser.newPage({ viewport: { width: 1100, height: 700 }, deviceScaleFactor: 1 });
let n = 0;
const shot = async (holdFrames = 1) => {
  for (let i = 0; i < holdFrames; i++) await page.screenshot({ path: `${FRAMES}/${String(n++).padStart(3, "0")}.png` });
};

await page.goto(`${WEB}/login`);
await shot(2);
await page.fill("#customerId", "AB10001");
await page.fill("#password", "Arya@2026");
await shot(2);
await page.click("#login-submit");
await page.waitForURL("**/dashboard");
await page.waitForSelector("#accounts .loading", { state: "detached" });
await shot(4);
await page.goto(`${WEB}/transfer`);
await page.waitForSelector("#beneficiary option[value=\"BEN-1\"]", { state: "attached" });
await page.selectOption("#beneficiary", { index: 1 });
await page.fill("#amount", "1500.75");
await page.fill("#remarks", "Dinner split");
await shot(3);
await page.click("text=Review transfer");
await page.waitForSelector("#step-review:not([hidden])");
await shot(3);
await page.click("#confirm");
await page.waitForSelector("#step-done:not([hidden])");
await shot(5); // typed 1500.75 ... look at what was actually sent
try {
  // Swagger UI loads from a CDN; skip the frame when offline.
  await page.goto(`${API}/docs`);
  await page.waitForSelector(".opblock", { timeout: 8000 });
  await shot(4);
} catch {
  console.warn("Swagger UI did not load (offline?), skipping that frame");
}
await browser.close();

execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", "1.25", "-i", `${FRAMES}/%03d.png`,
  "-vf", "scale=880:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4",
  "-loop", "0", `${OUT}demo.gif`]);
rmSync(FRAMES, { recursive: true, force: true });
console.log(`wrote ${OUT}demo.gif`);
