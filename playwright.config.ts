import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["html", { outputFolder: "test-results/playwright" }], ["list"]],
  use: {
    baseURL: process.env.MUSHIR_API_URL || "http://127.0.0.1:8000",
    trace: "on-first-retry",
  },
  globalSetup: require("./e2e/global-setup"),
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  timeout: 30_000,
});