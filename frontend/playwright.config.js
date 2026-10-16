import { defineConfig } from '@playwright/test';
import { resolve } from 'node:path';

const baseURL = process.env.CUSTRA_UI_URL || 'http://127.0.0.1:5178';

export default defineConfig({
  testDir: './tests',
  testMatch: '*.spec.js',
  workers: 1,
  timeout: 45_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL,
    trace: 'retain-on-failure',
    launchOptions: process.env.CUSTRA_CHROMIUM_PATH ? { executablePath: process.env.CUSTRA_CHROMIUM_PATH } : {},
  },
  projects: [
    { name: 'mobile', use: { viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' } },
    { name: 'desktop', use: { viewport: { width: 1440, height: 900 } } },
  ],
  webServer: process.env.CUSTRA_UI_URL ? undefined : [
    {
      command: '../backend/.venv/bin/python -m uvicorn demo_server:app --app-dir ../backend/tests/support --host 127.0.0.1 --port 8018',
      url: 'http://127.0.0.1:8018/api/health', reuseExistingServer: false,
      env: { PYTHONPATH: `${resolve('../backend')}:${resolve('../manufacturer-agent/app')}`, CUSTRA_APP_ORIGIN: baseURL },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5178',
      url: baseURL, reuseExistingServer: false,
      env: { CUSTRA_API_URL: 'http://127.0.0.1:8018' },
    },
  ],
});
