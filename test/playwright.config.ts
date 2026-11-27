import { defineConfig, devices } from "@playwright/test";
import { BASE_URL } from "./app";

export default defineConfig({
  testDir: "./e2e",
  // One app container is shared, so tests run one at a time.
  workers: 1,
  fullyParallel: false,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [["list"]],
  globalSetup: "./global-setup.ts",
  globalTeardown: "./global-teardown.ts",
  use: { baseURL: BASE_URL, trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
});
