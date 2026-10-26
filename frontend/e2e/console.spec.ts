import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const SHOTS = path.resolve(__dirname, "../../reports/screenshots");
fs.mkdirSync(SHOTS, { recursive: true });
const EXPECT_LIVE = process.env.E2E_EXPECT_LIVE === "1";
const SECRET_RE = /sk-[A-Za-z0-9_-]{16,}|OPENAI_API_KEY\s*[=:]/;

function watch(page: Page) {
  const errors: string[] = [];
  const leaks: string[] = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("response", async (r) => {
    const ct = r.headers()["content-type"] ?? "";
    if (!/json|text|javascript|ndjson/.test(ct)) return;
    const body = await r.text().catch(() => "");
    if (SECRET_RE.test(body)) leaks.push(r.url());
  });
  return { errors, leaks };
}

test("landing renders real causal graph and launches console", async ({ page }, info) => {
  const w = watch(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Simulate tomorrow before you build it.");
  await expect(page.getByRole("img", { name: /Causal graph version/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Historical backtests" })).toBeVisible();
  await expect(page.locator("text=2008_oil_spike")).toBeVisible();
  await page.screenshot({ path: path.join(SHOTS, `${info.project.name}-landing.png`), fullPage: true });
  await page.getByRole("link", { name: "Launch simulation" }).click();
  await expect(page).toHaveURL(/\/console/);
  await expect(page.getByTestId("engine-status")).toContainText("engine ok");
  expect(w.errors).toEqual([]);
  expect(w.leaks).toEqual([]);
});

test("engine builder run, agent run, analysis, trace, compare, arena", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop");
  const w = watch(page);
  const timings: Record<string, number> = {};
  await page.goto("/console");
  await expect(page.getByTestId("ai-status")).toBeVisible({ timeout: 30_000 });
  if (EXPECT_LIVE) await expect(page.getByTestId("ai-status")).toContainText("AI agents");

  // Builder: Reality Guard pre-check then engine run.
  await expect(page.getByTestId("guard-tier").first()).toBeVisible({ timeout: 20_000 });
  let t0 = Date.now();
  await page.getByTestId("builder-run").click();
  await expect(page.getByTestId("card-vmt")).toBeVisible({ timeout: 60_000 });
  timings.engine_run_ms = Date.now() - t0;
  const chart = page.getByRole("img", { name: /percentile spread/ });
  await expect(chart).toBeVisible();
  await chart.hover({ position: { x: 400, y: 120 } });
  await expect(page.locator(".tooltip")).toContainText("P10 to P90");
  await page.getByTestId("card-co2_kt").click();
  await expect(page.getByRole("img", { name: /CO2 emissions/ })).toBeVisible();

  // Natural language run through the agent stream.
  await page.getByTestId("question").fill("What if gasoline rises 30% for 12 months?");
  t0 = Date.now();
  await page.getByTestId("ask").click();
  await expect(page.getByRole("list", { name: "Pipeline stages" })).toBeVisible();
  await expect(page.getByTestId("run-header")).toBeVisible({ timeout: 180_000 });
  timings.analyze_ui_ms = Date.now() - t0;
  const mode = await page.getByTestId("run-mode").innerText();
  if (EXPECT_LIVE) expect(mode.toUpperCase()).toContain("AI AGENTS");
  await expect(page.getByTestId("card-vmt")).toBeVisible();
  await expect(page.getByTestId("analysis")).toContainText("Executive result");
  await page.screenshot({ path: path.join(SHOTS, "desktop-console-result.png"), fullPage: true });
  await page.getByTestId("tab-evidence").click();
  await expect(page.getByTestId("evidence")).toBeVisible();
  await page.getByTestId("evidence").locator("details").first().locator("summary").click();
  await expect(page.getByTestId("evidence")).toContainText("NEXUS-");
  await page.getByTestId("tab-critic").click();
  await expect(page.getByTestId("critic")).toContainText("Deterministic rules");
  await page.getByTestId("tab-trace").click();
  await expect(page.getByTestId("trace").locator("li").first()).toBeVisible();
  await page.screenshot({ path: path.join(SHOTS, "desktop-console-trace.png"), fullPage: true });

  // Compare baseline + slots and Policy Arena.
  await page.getByTestId("compare-run").click();
  await expect(page.getByTestId("compare").locator("tbody tr")).toHaveCount(6, { timeout: 60_000 });
  await page.getByTestId("arena-run").click();
  await expect(page.getByTestId("arena").locator("tbody tr").first()).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("arena")).toContainText("non-dominated");
  await page.getByTestId("arena").scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(SHOTS, "desktop-console-compare-arena.png"), fullPage: true });

  // Shareable run view.
  await page.getByRole("link", { name: "Open run view" }).click();
  await expect(page.getByText(/loaded from (server run store|this browser)/)).toBeVisible({ timeout: 30_000 });
  await page.screenshot({ path: path.join(SHOTS, "desktop-run-view.png"), fullPage: true });
  await page.goto("/run/NEXUS-2026-00000000");
  await expect(page.getByText("RUN NOT AVAILABLE ON THIS INSTANCE")).toBeVisible();

  fs.writeFileSync(path.resolve(__dirname, "../../reports/e2e_timings.json"), JSON.stringify({ ...timings, mode }, null, 2));
  expect(w.errors.filter((e) => !/404|Failed to load resource/.test(e))).toEqual([]);
  expect(w.leaks).toEqual([]);
});

test("mobile layout @mobile", async ({ page }, info) => {
  test.skip(info.project.name !== "mobile");
  const w = watch(page);
  await page.goto("/");
  await page.screenshot({ path: path.join(SHOTS, `${info.project.name}-landing.png`), fullPage: true });
  await page.goto("/console");
  await expect(page.getByTestId("engine-status")).toBeVisible();
  await page.getByTestId("builder-run").click();
  await expect(page.getByTestId("card-vmt")).toBeVisible({ timeout: 60_000 });
  await page.screenshot({ path: path.join(SHOTS, `${info.project.name}-console.png`), fullPage: true });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  expect(w.errors).toEqual([]);
  expect(w.leaks).toEqual([]);
});
