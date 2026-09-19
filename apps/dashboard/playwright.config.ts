import { defineConfig, devices } from "@playwright/test";

// Viewport matrix per MASTER-AUFTRAG LOGOS1-RESEARCH-OPERATING-SYSTEM-DASHBOARD-R1 §58.
const desktop = (name: string, width: number, height: number) => ({ name, use: { ...devices["Desktop Chrome"], viewport: { width, height } } });

export default defineConfig({
  globalSetup: "./e2e/global-setup.ts",
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000, toHaveScreenshot: { maxDiffPixelRatio: 0.02 } },
  fullyParallel: false,
  retries: 1,
  reporter: [["list"], ["html", { open: "never", outputFolder: "e2e/report" }], ["json", { outputFile: "e2e/results/last-run.json" }]],
  outputDir: "e2e/results/artifacts",
  use: { baseURL: process.env.DASHBOARD_URL ?? "http://127.0.0.1:3000", trace: "on-first-retry", screenshot: "only-on-failure", video: "retain-on-failure" },
  projects: [
    desktop("desktop-1920", 1920, 1080),
    desktop("desktop-1440", 1440, 900),
    desktop("desktop-1366", 1366, 768),
    desktop("desktop-1280", 1280, 720),
    { name: "tablet-1024", use: { ...devices["Desktop Chrome"], viewport: { width: 1024, height: 768 } } },
    { name: "mobile-390", use: { ...devices["iPhone 13"], browserName: "chromium", viewport: { width: 390, height: 844 } } },
  ],
});
