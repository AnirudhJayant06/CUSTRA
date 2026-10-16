import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

const controlsURL = process.env.CUSTRA_TEST_CONTROL_API || 'http://127.0.0.1:8018';

test.beforeEach(async ({ request }) => {
  test.skip(Boolean(process.env.CUSTRA_UI_URL) && !process.env.CUSTRA_TEST_CONTROL_API,
    'Failure/session fixtures require an explicitly configured test-only control API');
  expect((await request.post(`${controlsURL}/test/reset`)).ok()).toBeTruthy();
});

async function login(page) {
  const credentials = process.env.CUSTRA_TEST_USERNAME && process.env.CUSTRA_TEST_PASSWORD
    ? { username: process.env.CUSTRA_TEST_USERNAME, password: process.env.CUSTRA_TEST_PASSWORD }
    : JSON.parse(readFileSync(process.env.CUSTRA_E2E_AUTH_PATH || '/tmp/custra-e2e-credentials.json', 'utf8'));
  await page.goto('/login');
  await page.getByLabel('Username', { exact: true }).fill(credentials.username);
  await page.getByLabel('Password', { exact: true }).fill(credentials.password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Product Vault' })).toBeVisible();
}

async function seedProduct(page) {
  await login(page);
  await page.getByRole('link', { name: 'Account settings' }).click();
  await page.locator('#profile-name').fill('Fictional Reviewer');
  await page.locator('#profile-phone').fill('9999999999');
  await page.locator('#profile-email').fill('fictional@example.test');
  await page.getByRole('button', { name: 'Save profile' }).click();
  await expect(page.getByText('Profile saved.')).toBeVisible();
  await page.getByRole('link', { name: 'Vault', exact: true }).click();
  await page.getByLabel('Product category').fill('Smartphone');
  await page.getByLabel('Brand', { exact: true }).fill('Samsung');
  await page.getByLabel('Model or product name').fill('Fictional Phone');
  await page.getByRole('button', { name: 'Save product' }).click();
  await expect(page.getByRole('heading', { name: 'Fictional Phone' })).toBeVisible();
}

async function openComplaintForm(page) {
  await page.getByRole('tab', { name: 'Complaints', exact: true }).click();
  await page.getByRole('link', { name: 'Start a complaint' }).click();
  await page.getByLabel('Issue summary').fill('Fictional device problem');
  await page.getByLabel('Issue description').fill('The fictional device stops during use.');
}

test('saved Vault → automated case → final dialog → explicit closure', async ({ page, request }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await seedProduct(page);
  await page.getByLabel('Choose a document').setInputFiles({
    name: 'fictional-invoice.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.7\nFictional invoice'),
  });
  await page.getByRole('button', { name: 'Upload document' }).click();
  const fileLink = page.getByRole('link', { name: 'fictional-invoice.pdf' });
  await expect(fileLink).toBeVisible();
  const document = await page.request.get(await fileLink.getAttribute('href'));
  expect(document.status()).toBe(200);
  expect(document.headers()['content-disposition']).toContain('attachment;');
  await openComplaintForm(page);
  await page.getByRole('button', { name: 'Add address', exact: true }).click();
  const addressDialog = page.getByRole('dialog', { name: 'Add address', exact: true });
  await page.keyboard.press('Shift+Tab');
  expect(await addressDialog.evaluate((element) => element.contains(document.activeElement))).toBeTruthy();
  await page.locator('#address-label').fill('Unsaved address');
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.getByLabel('Issue summary')).toHaveValue('Fictional device problem');
  await page.getByRole('button', { name: 'Add address', exact: true }).click();
  await page.locator('#address-label').fill('Fictional home');
  await page.locator('#address-line1').fill('1 Fiction Lane');
  await page.locator('#address-city').fill('Pune');
  await page.locator('#address-region').fill('Maharashtra');
  await page.locator('#address-postal').fill('411001');
  await page.getByRole('button', { name: 'Save address' }).click();
  await expect(page.getByLabel('Service address')).toContainText('Fictional home');
  await page.getByRole('button', { name: 'Start complaint', exact: true }).click({ clickCount: 2 });
  await expect(page.getByText('What product needs service?', { exact: true })).toBeVisible();
  await page.reload();
  const dialog = page.getByRole('dialog', { name: 'Choose an appointment' });
  await expect(dialog).toBeVisible();
  expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBeTruthy();
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(page.getByText('Status: AWAITING APPOINTMENT', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Simulated appointment confirmed' })).not.toBeVisible();
  const state = await (await request.get(`${controlsURL}/test/state`)).json();
  expect(state.cases).toHaveLength(1);
  const caseId = state.cases[0].id;
  const events = await (await page.request.get(`/api/complaints/${caseId}/events`)).json();
  expect(events).toHaveLength(9);
  expect(new Set(events.map((event) => event.eventId)).size).toBe(9);
  await expect(page.locator('textarea')).toHaveCount(0);
  await page.getByLabel('Choose a case photo').setInputFiles({
    name: 'fictional-device.png', mimeType: 'image/png',
    buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=', 'base64'),
  });
  await page.getByRole('button', { name: 'Upload photo', exact: true }).click();
  await expect(page.getByRole('link', { name: 'fictional-device.png', exact: true })).toBeVisible();
  await page.reload();
  await expect(dialog).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('heading', { name: 'Case photos', exact: true }).scrollIntoViewIfNeeded();
  await expect(page.getByRole('img', { name: 'Stored fictional-device.png' })).toBeVisible();
  await expect(page.getByRole('img', { name: 'Stored fictional-device.png' })).toHaveJSProperty('naturalWidth', 1);
  await page.getByRole('button', { name: 'Choose appointment', exact: true }).click();
  await dialog.getByRole('radio').first().check();
  await dialog.getByRole('button', { name: 'Confirm appointment', exact: true }).click();
  await expect(page.getByText('Status: BOOKED', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText('Status: BOOKED', { exact: true })).toBeVisible();
  await page.getByRole('checkbox', { name: 'The issue has been resolved.' }).check();
  await page.getByRole('button', { name: 'Confirm issue resolved' }).click();
  await expect(page.getByText('Status: CLOSED', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
  expect(errors).toEqual([]);
  await page.getByRole('link', { name: 'Account settings' }).click();
  await expect(page.getByText('Fictional home', { exact: true })).toBeVisible();
  await page.route('**/api/auth/logout', (route) => route.abort('failed'));
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('alert')).toHaveText('Could not sign out. Check your connection and try again.');
  await page.unroute('**/api/auth/logout');
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Sign in to the demo.' })).toBeVisible();
});

test('model failure stops progress and explicit retry resumes', async ({ page, request }) => {
  await seedProduct(page);
  await openComplaintForm(page);
  await request.post(`${controlsURL}/test/fail-model`);
  await page.getByRole('button', { name: 'Start complaint', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Retry saved step' })).toBeVisible();
  await expect(page.getByText('Working on the next saved step…')).not.toBeVisible();
  await page.getByRole('button', { name: 'Retry saved step' }).click();
  await expect(page.getByRole('dialog', { name: 'Choose an appointment' })).toBeVisible();
});

test('expired session returns to login', async ({ page, request }) => {
  await login(page);
  await request.post(`${controlsURL}/test/expire-session`);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Sign in to the demo.' })).toBeVisible();
});
