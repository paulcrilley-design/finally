import { defineConfig } from "@playwright/test";

import { URL } from "./e2e/app.mjs";

// One app container and one database, so the tests run one at a time, in file order.
export default defineConfig({
  testDir: "e2e",
  workers: 1,
  fullyParallel: false,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: "list",
  globalSetup: "./e2e/setup.mjs",
  globalTeardown: "./e2e/teardown.mjs",
  use: { baseURL: URL, viewport: { width: 1440, height: 900 }, trace: "retain-on-failure" },
});
