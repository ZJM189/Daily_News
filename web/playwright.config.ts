import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 90_000,
  workers: 1,
  reporter: "list",
  use: {
    channel: "chromium",
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:3100",
    screenshot: "only-on-failure",
    trace: "retain-on-failure"
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 1000 } } },
    { name: "mobile", use: { ...devices["Pixel 7"] } }
  ]
});
