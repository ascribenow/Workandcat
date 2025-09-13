import { defineConfig, devices } from '@playwright/test';

const API_BASE = process.env.API_BASE ?? 'http://localhost:3000';

export default defineConfig({
  testDir: __dirname,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  workers: 4,
  fullyParallel: true,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: API_BASE,
    extraHTTPHeaders: (() => {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (process.env.E2E_BEARER) headers['Authorization'] = `Bearer ${process.env.E2E_BEARER}`;
      return headers;
    })(),
  },
  projects: [
    { name: 'API', use: { ...devices['Desktop Chrome'] } },
  ],
});