import { expect, test, type Page } from '@playwright/test';

const adminEmail = 'phase4-admin-e2e@example.com';
const adminPassword = 'Phase4E2EAdminPass123!';
const candidateEmail = 'candidate@aairo.ai';
const candidatePassword = 'CandidatePass123!';

async function signIn(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.getByPlaceholder('candidate@aairo.ai').fill(email);
  await page.getByPlaceholder('••••••••••••').fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

test('Phase 4 browser journey: admin publishes question/module content and candidate practices/completes with persisted progress', async ({ page }) => {
  const stamp = Date.now();
  const questionText = `Phase 4 browser question ${stamp}: describe one way to investigate a service regression.`;
  const moduleTitle = `Phase 4 browser module ${stamp}`;

  await signIn(page, adminEmail, adminPassword);
  await page.goto('/admin/questions');
  await page.getByLabel('Industry').selectOption({ label: 'Information Technology' });
  await page.getByLabel('Question type').selectOption('short_answer');
  await page.getByLabel('Subject').fill('Browser Verification');
  await page.getByLabel('Topic').fill('Service Regression');
  await page.getByLabel('Interview round').fill('Technical');
  await page.getByLabel('Content provenance').selectOption('editorially_reviewed');
  await page.getByRole('textbox', { name: 'Question', exact: true }).fill(questionText);
  await page.getByLabel('Expected answer').fill('Compare service telemetry with a known healthy baseline.');
  await page.getByRole('button', { name: 'Save as draft' }).click();
  const questionCard = page.locator('article').filter({ hasText: questionText });
  await expect(questionCard).toBeVisible();
  await expect(questionCard.getByText('draft', { exact: true })).toBeVisible();
  await questionCard.getByRole('button', { name: 'Submit for review' }).click();
  await expect(questionCard.getByText('pending review', { exact: true })).toBeVisible();
  await questionCard.getByRole('button', { name: 'Approve' }).click();
  await expect(questionCard.getByText('approved')).toBeVisible();
  await questionCard.getByRole('button', { name: 'Publish' }).click();
  await expect(questionCard.getByText('published')).toBeVisible();

  await page.goto('/admin/modules');
  await page.getByLabel('Industry').selectOption({ label: 'Information Technology' });
  await page.getByLabel('Title').fill(moduleTitle);
  await page.getByLabel('Description').fill('Browser verified learning content with persisted candidate progress.');
  await page.getByRole('button', { name: 'Create draft' }).click();
  const moduleCard = page.locator('article').filter({ hasText: moduleTitle });
  await expect(moduleCard).toBeVisible();
  await moduleCard.getByRole('button', { name: 'Add lesson' }).click();
  await page.getByPlaceholder('Lesson title').fill('Persisted browser lesson');
  await page.getByPlaceholder('Lesson content').fill('Review telemetry, identify a baseline, and state a measurable next step.');
  await moduleCard.getByRole('button', { name: 'Save lesson' }).click();
  await expect(moduleCard.getByText('Persisted browser lesson')).toBeVisible();
  await moduleCard.getByRole('button', { name: 'Preview' }).click();
  await expect(moduleCard.getByRole('region', { name: `${moduleTitle} preview` }).getByText('Review telemetry, identify a baseline, and state a measurable next step.')).toBeVisible();
  await moduleCard.getByRole('button', { name: 'Publish' }).click();
  await expect(moduleCard.getByText('published')).toBeVisible();

  await page.evaluate(() => localStorage.clear());
  await signIn(page, candidateEmail, candidatePassword);
  await page.goto('/question-bank');
  await expect(page.getByRole('heading', { name: 'Question Bank' })).toBeVisible();
  const search = page.getByPlaceholder('Search questions, subjects, topics');
  await search.fill(questionText);
  await search.press('Enter');
  await expect(page.getByText(questionText)).toBeVisible();
  await page.locator('article').filter({ hasText: questionText }).getByRole('button', { name: 'Practice this question →' }).click();
  await page.getByLabel('Your answer').fill('A');
  await page.getByRole('button', { name: 'Submit answer' }).click();
  await expect(page.getByRole('status')).toContainText(/evaluation|Correct|Not quite/i);
  await page.getByRole('button', { name: 'View practice history' }).click();
  await expect(page.getByRole('region', { name: 'Practice history' }).getByText(questionText)).toBeVisible();

  await page.goto('/modules');
  const moduleButton = page.getByRole('navigation', { name: 'Available learning modules' }).getByRole('button', { name: new RegExp(moduleTitle) });
  await expect(moduleButton).toBeVisible();
  await moduleButton.click();
  await page.getByRole('button', { name: 'Start module' }).click();
  await page.getByRole('button', { name: 'Mark complete' }).click();
  await expect(page.getByText('Completed', { exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole('navigation', { name: 'Available learning modules' }).getByRole('button', { name: new RegExp(moduleTitle) }).click();
  await expect(page.getByText('Completed', { exact: true })).toBeVisible();
});
