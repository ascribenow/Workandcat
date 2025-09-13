import { defineConfig, devices } from '@playwright/test';

const API_BASE = process.env.API_BASE ?? 'http://localhost:3000';

export default defineConfig({
  testDir: __dirname,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  workers: 4,
  fullyParallel: true,
  globalSetup: require.resolve('./global.setup'),
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: API_BASE,
    extraHTTPHeaders: { 'Content-Type': 'application/json' },
  },
  projects: [
    { name: 'API', use: { ...devices['Desktop Chrome'] } },
  ],
});