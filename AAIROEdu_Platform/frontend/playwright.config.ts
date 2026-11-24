import { defineConfig } from '@playwright/test';

const frontendPort = Number(process.env.AAIRO_E2E_WEB_PORT || 5174);
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${frontendPort}`;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: [['list']],
  use: {
    baseURL,
    channel: 'chrome',
    headless: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: '../backend/venv/bin/python ../backend/scripts/run_e2e_server.py',
      url: 'http://127.0.0.1:8001/health',
      timeout: 180_000,
      reuseExistingServer: false,
      env: {
        AAIRO_E2E_DATABASE: 'aairo_phase3_e2e',
        AAIRO_E2E_API_PORT: '8001',
        RESUME_UPLOAD_RATE_LIMIT: '3',
      },
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      url: baseURL,
      timeout: 60_000,
      reuseExistingServer: false,
      env: { VITE_API_PROXY_TARGET: 'http://127.0.0.1:8001' },
    },
  ],
});
