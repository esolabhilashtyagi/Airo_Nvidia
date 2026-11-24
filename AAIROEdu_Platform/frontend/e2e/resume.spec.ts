import { expect, test, type Page, type APIRequestContext } from '@playwright/test';

const API = 'http://127.0.0.1:8001/api/v1';
const password = 'E2eResumePass123!';
let email = '';
let resumeId = '';
let dragDropResumeId = '';
let analysisAvailable = false;

function makePdf(lines: string[]): Buffer {
  const commands = lines.map((line, index) =>
    `${index === 0 ? '72 720 Td' : '0 -24 Td'} (${line.replace(/[\\()]/g, '\\$&')}) Tj`,
  ).join('\n');
  const stream = `BT /F1 14 Tf\n${commands}\nET`;
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    `<< /Length ${Buffer.byteLength(stream, 'ascii')} >>\nstream\n${stream}\nendstream`,
  ];
  let pdf = '%PDF-1.4\n';
  const offsets = [0];
  for (let index = 0; index < objects.length; index += 1) {
    offsets.push(Buffer.byteLength(pdf, 'ascii'));
    pdf += `${index + 1} 0 obj\n${objects[index]}\nendobj\n`;
  }
  const xrefOffset = Buffer.byteLength(pdf, 'ascii');
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets.slice(1)) pdf += `${String(offset).padStart(10, '0')} 00000 n \n`;
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;
  return Buffer.from(pdf, 'ascii');
}

const candidatePdf = (variant = '') => makePdf([
  'E2E Resume Candidate',
  'Email: candidate.e2e@example.com',
  'Skills',
  'Python, PostgreSQL',
  'Experience',
  'Built reliable test suites 2022 - 2024',
  ...(variant ? [`Upload variant: ${variant}`] : []),
]);

async function login(page: Page) {
  await page.goto('/login');
  await page.getByPlaceholder('candidate@aairo.ai').fill(email);
  await page.getByPlaceholder('••••••••••••').fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

async function createApiCandidate(request: APIRequestContext, candidateEmail: string) {
  const registered = await request.post(`${API}/auth/register`, {
    data: { email: candidateEmail, password, full_name: 'Other E2E Candidate' },
  });
  expect(registered.status()).toBe(201);
  const loggedIn = await request.post(`${API}/auth/login`, { data: { email: candidateEmail, password } });
  expect(loggedIn.ok()).toBeTruthy();
  return (await loggedIn.json()).data.access_token as string;
}

test.describe.serial('Phase 3 resume workflow', () => {
  test('registers, uploads a real PDF, and verifies extracted details', async ({ page }) => {
    email = `resume.e2e.${Date.now()}@example.com`;
    await page.goto('/register');
    await page.getByPlaceholder('e.g. Maya Patel').fill('E2E Resume Candidate');
    await page.getByPlaceholder('candidate@example.com').fill(email);
    await page.getByPlaceholder('Min. 8 characters').fill(password);
    await page.getByRole('button', { name: 'Create Account' }).click();
    // Registration lands on the dashboard; it must clearly expose the incomplete onboarding action.
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByText(/Your onboarding profile is incomplete/)).toBeVisible();

    await page.goto('/resume');
    await expect(page.getByRole('heading', { name: 'My resumes' })).toBeVisible();
    await page.locator('input[type="file"]').setInputFiles({
      name: 'resume-e2e.pdf', mimeType: 'application/pdf', buffer: candidatePdf(),
    });
    await expect(page.getByRole('heading', { name: 'resume-e2e.pdf' })).toBeVisible();
    const parsedData = page.getByLabel('Editable extracted resume data in JSON');
    await expect(parsedData).toHaveValue(/candidate\.e2e@example\.com/);
    await expect(parsedData).toHaveValue(/Python/);
    resumeId = page.url().split('/').at(-1) || '';
    expect(resumeId).toMatch(/^[0-9a-f-]{36}$/i);
  });

  test('saves parsed-data corrections and reloads them from the API', async ({ page }) => {
    await login(page);
    await page.goto(`/resume/${resumeId}`);
    const parsedData = page.getByLabel('Editable extracted resume data in JSON');
    const corrected = JSON.parse(await parsedData.inputValue());
    corrected.contact_info.full_name = 'E2E Resume Candidate Corrected';
    await parsedData.fill(JSON.stringify(corrected, null, 2));
    await page.getByRole('button', { name: 'Save corrections' }).click();
    await expect(page.getByRole('status')).toContainText('saved as a new resume version');
    await page.reload();
    await expect(page.getByLabel('Editable extracted resume data in JSON')).toHaveValue(/E2E Resume Candidate Corrected/);
  });

  test('supports file validation, drag-and-drop, and extraction retry', async ({ page }) => {
    await login(page);
    await page.goto('/resume');
    const input = page.locator('input[type="file"]');
    await input.setInputFiles({ name: 'unsupported.txt', mimeType: 'text/plain', buffer: Buffer.from('unsupported') });
    await expect(page.getByRole('alert')).toContainText('Choose a PDF, DOCX, PNG, JPG, or JPEG');

    const dropTarget = page.getByRole('button', { name: /Drop a resume here or browse files/ });
    const encodedPdf = candidatePdf('drag-drop').toString('base64');
    const dropResult = await dropTarget.evaluate((element, base64) => {
      const bytes = Uint8Array.from(atob(base64), (character) => character.charCodeAt(0));
      const transfer = new DataTransfer();
      transfer.items.add(new File([bytes], 'resume-drag-drop.pdf', { type: 'application/pdf' }));
      element.dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: transfer }));
      const drop = new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: transfer });
      element.dispatchEvent(drop);
      return { files: transfer.files.length, prevented: drop.defaultPrevented };
    }, encodedPdf);
    expect(dropResult).toEqual({ files: 1, prevented: true });
    await expect(page.getByRole('heading', { name: 'resume-drag-drop.pdf' })).toBeVisible();
    dragDropResumeId = page.url().split('/').at(-1) || '';
    expect(dragDropResumeId).toMatch(/^[0-9a-f-]{36}$/i);

    await page.getByRole('link', { name: 'My resumes' }).click();
    await page.locator('input[type="file"]').setInputFiles({
      name: 'blank-resume.pdf', mimeType: 'application/pdf', buffer: makePdf([]),
    });
    await expect(page.getByText(/No readable text was found/)).toBeVisible();
    await page.getByRole('button', { name: 'Retry extraction' }).click();
    await expect(page.getByText(/No readable text was found/)).toBeVisible();
  });

  test('shows a genuine AI analysis or a truthful unavailable state', async ({ page }) => {
    await login(page);
    await page.goto(`/resume/${resumeId}/analysis`);
    await page.getByRole('button', { name: 'Analyze resume' }).click();
    const unavailable = page.getByRole('heading', { name: 'Analysis is unavailable' });
    const completed = page.getByText('Overall rubric score');
    await expect(unavailable.or(completed)).toBeVisible({ timeout: 70_000 });
    analysisAvailable = await completed.isVisible().catch(() => false);
    if (analysisAvailable) {
      await expect(page.getByText('out of 100')).toBeVisible();
    } else {
      await expect(page.getByText(/No sample scores or suggestions are shown/)).toBeVisible();
      await page.getByRole('link', { name: 'Enhancements' }).click();
      await expect(page.getByText(/No verified suggestions are available/)).toBeVisible();
      await page.getByRole('button', { name: 'Generate suggestions' }).click();
      await expect(page.getByRole('alert')).toContainText(/not configured|unavailable/i);
    }
  });

  test('reviews live suggestions and stores accepted edits as a version', async ({ page }) => {
    test.skip(!analysisAvailable, 'Live Gemini is not configured; the explicit unavailable state is covered in the analysis test.');
    await login(page);
    await page.goto(`/resume/${resumeId}/enhancement`);
    await page.getByRole('button', { name: 'Refresh suggestions' }).click();
    const acceptButtons = page.getByRole('button', { name: 'Accept and save version' });
    await expect(acceptButtons.first()).toBeVisible({ timeout: 70_000 });
    await page.getByLabel(/Proposed wording/).first().fill('Built reliable test suites');
    await acceptButtons.first().click();
    await expect(page.getByRole('status')).toContainText('accepted and saved as a new version');
    await page.getByRole('link', { name: 'Version history' }).click();
    await expect(page.getByRole('heading', { name: 'Version 3' })).toBeVisible();

    const rejectButtons = page.getByRole('button', { name: 'Reject' });
    if (await rejectButtons.count()) {
      await rejectButtons.first().click();
      await expect(page.getByText('Rejected', { exact: true }).first()).toBeVisible();
    }
  });

  test('persists resumes after logout and login', async ({ page }) => {
    await login(page);
    await page.goto(`/resume/${resumeId}/versions`);
    await expect(page.getByRole('heading', { name: 'Version 2' })).toBeVisible();
    await page.getByRole('button', { name: new RegExp(`Open user menu for E2E Resume Candidate`) }).click();
    await page.getByRole('button', { name: 'Sign Out' }).click();
    await expect(page).toHaveURL(/\/login$/);
    await login(page);
    await page.goto('/resume');
    const resumeLink = page.getByRole('link', { name: 'resume-e2e.pdf', exact: true });
    await expect(resumeLink).toBeVisible();
    await resumeLink.click();
    await expect(page.getByLabel('Editable extracted resume data in JSON')).toHaveValue(/E2E Resume Candidate Corrected/);
  });

  test('denies Candidate A access to Candidate B resume data', async ({ page, request }) => {
    await login(page);
    const otherEmail = `resume.e2e.other.${Date.now()}@example.com`;
    const otherToken = await createApiCandidate(request, otherEmail);
    const upload = await request.post(`${API}/resumes/upload`, {
      headers: { Authorization: `Bearer ${otherToken}` },
      multipart: { file: { name: 'other-candidate.pdf', mimeType: 'application/pdf', buffer: candidatePdf() } },
    });
    expect(upload.status()).toBe(201);
    const otherResumeId = (await upload.json()).data.id as string;

    await page.goto(`/resume/${otherResumeId}`);
    await expect(page.getByRole('alert')).toContainText('Resume not found');
  });

  test('keeps the resume library usable at desktop, laptop, tablet, and mobile widths', async ({ page }) => {
    await login(page);
    const viewports = [
      { width: 1440, height: 900 },
      { width: 1280, height: 800 },
      { width: 768, height: 1024 },
      { width: 390, height: 844 },
    ];
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.goto('/resume');
      await expect(page.getByRole('heading', { name: 'My resumes' })).toBeVisible();
      const dimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth }));
      expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.width + 1);
      if (viewport.width < 768) {
        await page.getByRole('button', { name: 'Open navigation menu' }).click();
        await expect(page.getByRole('link', { name: 'My Resume' })).toBeVisible();
        await page.getByRole('button', { name: 'Close navigation menu' }).click();
      }
    }
  });

  test('enforces the configured upload rate limit with a retry interval', async ({ request }) => {
    const rateEmail = `resume.e2e.limit.${Date.now()}@example.com`;
    const token = await createApiCandidate(request, rateEmail);
    for (let index = 0; index < 3; index += 1) {
      const uploaded = await request.post(`${API}/resumes/upload`, {
        headers: { Authorization: `Bearer ${token}` },
        multipart: {
          file: {
            name: `rate-limit-${index}.pdf`,
            mimeType: 'application/pdf',
            buffer: makePdf(['Rate Limit Test', `Unique entry ${index}`, 'Skills: Python']),
          },
        },
      });
      expect(uploaded.status()).toBe(201);
    }
    const limited = await request.post(`${API}/resumes/upload`, {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        file: { name: 'rate-limit-final.pdf', mimeType: 'application/pdf', buffer: candidatePdf() },
      },
    });
    expect(limited.status()).toBe(429);
    expect(Number(limited.headers()['retry-after'])).toBeGreaterThan(0);
  });
});
