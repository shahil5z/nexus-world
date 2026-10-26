import { defineConfig, devices } from "@playwright/test";

// Expects the backend on :8000 and `next start` on :3000 (NEXUS_BACKEND_URL=http://127.0.0.1:8000). See docs/PHASE-4-FRONTEND.md.
export default defineConfig({
  testDir: "./e2e",
  timeout: 240_000,
  expect: { timeout: 15_000 },
  workers: 1,
  reporter: [["list"], ["json", { outputFile: "../reports/e2e_results.json" }]],
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000", trace: "off" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    { name: "mobile", use: { ...devices["Pixel 7"] }, grep: /@mobile/ },
  ],
});
