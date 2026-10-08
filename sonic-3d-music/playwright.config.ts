import { defineConfig, devices } from "@playwright/test";

// Pruebas end-to-end contra la build de producción: `npm run build && npm run test:e2e`.
const puerto = Number(process.env.E2E_PORT ?? 3100);
const url = `http://127.0.0.1:${puerto}`;

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 180_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: url,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "escritorio", use: { ...devices["Desktop Chrome"] } },
    { name: "movil", use: { ...devices["Pixel 7"] }, testMatch: /movil\.spec\.ts/ },
  ],
  webServer: {
    command: `npx next start -p ${puerto}`,
    url,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
