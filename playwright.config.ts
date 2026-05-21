import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";

const localPython = process.platform === "win32" ? ".\\.venv\\Scripts\\python.exe" : ".venv/bin/python";
const pythonCommand = existsSync(localPython) ? localPython : "python";
const baseURL = process.env.MUSHIR_API_URL || "http://127.0.0.1:8017";

export default defineConfig({
  testDir: "./e2e",
  outputDir: "test-results/e2e-artifacts",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["html", { outputFolder: "playwright-report", open: "never" }], ["list"]],
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  globalSetup: "./e2e/global-setup",
  webServer: process.env.MUSHIR_API_URL
    ? undefined
    : {
        command: `${pythonCommand} -m uvicorn src.api.main:app --host 127.0.0.1 --port 8017`,
        url: `${baseURL}/health`,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  timeout: 30_000,
});
