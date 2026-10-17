import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
const controlsURL = process.env.CUSTRA_TEST_CONTROL_API || 'http://127.0.0.1:8018';
test.beforeEach(async ({ request }) => {
  test.skip(Boolean(process.env.CUSTRA_UI_URL) && !process.env.CUSTRA_TEST_CONTROL_API, 'Use only the explicit fictional fixture control API');
  expect((await request.post(`${controlsURL}/test/reset`)).ok()).toBeTruthy();
});
async function login(page) {
  const auth = process.env.CUSTRA_TEST_USERNAME && process.env.CUSTRA_TEST_PASSWORD ? { username: process.env.CUSTRA_TEST_USERNAME, password: process.env.CUSTRA_TEST_PASSWORD } : JSON.parse(readFileSync(process.env.CUSTRA_E2E_AUTH_PATH || '/tmp/custra-e2e-credentials.json', 'utf8'));
  await page.goto('/login'); await page.getByLabel('Username', { exact: true }).fill(auth.username); await page.getByLabel('Password', { exact: true }).fill(auth.password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click(); await expect(page.getByRole('heading', { name: 'Active complaints', exact: true })).toBeVisible();
}
async function seedProduct(page) {
  await login(page); await page.getByLabel('Profile menu', { exact: true }).click(); await page.getByRole('link', { name: 'Profile', exact: true }).click();
  await page.locator('#profile-name').fill('Fictional Reviewer'); await page.locator('#profile-phone').fill('9999999999'); await page.locator('#profile-email').fill('fictional@example.test');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click(); await expect(page.getByText('Profile saved.')).toBeVisible();
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Products', exact: true }).click();
  await page.getByRole('link', { name: 'Add product', exact: true }).click(); await page.getByLabel('Product type', { exact: true }).selectOption('smartphone');
  await page.getByLabel('Brand', { exact: true }).selectOption('samsung'); await page.locator('#nickname').fill('Fictional Phone');
  await page.getByRole('button', { name: 'Save product', exact: true }).click(); await expect(page.getByRole('heading', { name: 'Fictional Phone', exact: true })).toBeVisible();
}
async function openComplaintForm(page) {
  await page.getByRole('link', { name: 'Register a complaint', exact: true }).click(); await page.getByLabel('What’s wrong?', { exact: true }).fill('The fictional device stops during use.');
}
async function choosePreference(page) {
  await page.getByRole('button', { name: /Preferred date/ }).click(); const picker = page.getByRole('dialog', { name: 'Preferred date', exact: true });
  await picker.locator('button[aria-pressed="false"]:not([disabled])').first().click();
  const time = page.getByRole('dialog', { name: 'Preferred time', exact: true });
  await expect(time.getByText('Unavailable', { exact: true }).first()).toBeVisible(); await expect(time.getByRole('button', { name: 'Change date', exact: true })).toBeEnabled();
  await time.getByRole('radio').first().check(); await time.getByRole('button', { name: 'Save preference', exact: true }).click();
}
async function selectDocument(page, file) {
  await page.getByRole('button', { name: 'Add document', exact: true }).click();
  const picker = page.getByRole('dialog', { name: 'Add document', exact: true });
  await expect(picker.getByRole('button', { name: 'Take photo', exact: true })).toBeVisible();
  await expect(picker.getByRole('button', { name: 'Choose photo', exact: true })).toBeVisible();
  const choosing = page.waitForEvent('filechooser');
  await picker.getByRole('button', { name: 'Upload file', exact: true }).click();
  await (await choosing).setFiles(file);
}

test('saved product → preferred visit → agent chat → explicit booking and closure', async ({ page, request }, testInfo) => {
  const errors = []; page.on('pageerror', (e) => errors.push(e.message)); await seedProduct(page);
  await selectDocument(page, { name: 'fictional-invoice.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.7\nFictional invoice') });
  await page.getByRole('button', { name: 'Upload document', exact: true }).click();
  const file = page.getByRole('link', { name: 'fictional-invoice.pdf', exact: true }); await expect(file).toBeVisible();
  const download = await page.request.get(await file.getAttribute('href')); expect(download.status()).toBe(200); expect(download.headers()['content-disposition']).toContain('attachment;');
  await openComplaintForm(page);
  await page.getByRole('button', { name: /Service address/ }).click(); await page.getByRole('button', { name: 'Add address', exact: true }).click();
  const addressDialog = page.getByRole('dialog', { name: 'Add address', exact: true }); await page.keyboard.press('Shift+Tab'); expect(await addressDialog.evaluate((el) => el.contains(document.activeElement))).toBe(true);
  await page.locator('#address-label').fill('Unsaved'); await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.getByLabel('What’s wrong?', { exact: true })).toHaveValue('The fictional device stops during use.');
  await page.getByRole('button', { name: /Service address/ }).click(); await page.getByRole('button', { name: 'Add address', exact: true }).click();
  await page.locator('#address-label').fill('Fictional home'); await page.locator('#address-line1').fill('1 Fiction Lane'); await page.locator('#address-city').fill('Pune');
  await page.locator('#address-region').fill('Maharashtra'); await page.locator('#address-postal').fill('411001'); await page.getByRole('checkbox', { name: 'Use as default address' }).check();
  await page.getByRole('button', { name: 'Save address', exact: true }).click(); await expect(page.getByRole('button', { name: /Service address/ })).toContainText('Fictional home');
  await choosePreference(page);
  const savedPreference = await page.getByRole('button', { name: /Preferred date/ }).locator('small').textContent();
  await page.getByRole('button', { name: /Preferred date/ }).click();
  await expect(page.getByRole('dialog', { name: 'Preferred date', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  await expect(page.getByRole('button', { name: /Preferred date/ }).locator('small')).toHaveText(savedPreference);
  await page.screenshot({ path: testInfo.outputPath('complaint-form.png'), fullPage: true }); await page.getByRole('button', { name: 'Register complaint', exact: true }).click({ clickCount: 2 });
  const visit = page.getByRole('dialog', { name: 'Confirm technician visit', exact: true }); await expect(visit).toBeVisible();
  await expect(visit.getByRole('button', { name: 'Choose later', exact: true })).toHaveCount(0);
  await expect(visit.getByRole('button', { name: /Change date|Choose date/ })).toHaveCount(0);
  await expect(visit.getByRole('button', { name: 'Close', exact: true })).toBeVisible();
  await visit.getByRole('heading').click(); await expect(visit).toBeVisible();
  await page.mouse.click(2, 2); await expect(visit).not.toBeVisible();
  await page.getByRole('button', { name: 'Confirm technician visit', exact: true }).click();
  await visit.getByRole('button', { name: 'Close', exact: true }).click(); await expect(visit).not.toBeVisible();
  await page.getByRole('button', { name: 'Confirm technician visit', exact: true }).click();
  await page.screenshot({ path: testInfo.outputPath('visit-confirmation.png') });
  const state = await (await request.get(`${controlsURL}/test/state`)).json(); expect(state.cases).toHaveLength(1); const row = state.cases[0]; expect(row.preferredSlotId).toBeTruthy();
  const events = await (await page.request.get(`/api/complaints/${row.id}/events`)).json(); expect(events).toHaveLength(9); expect(new Set(events.map((e) => e.eventId)).size).toBe(9);
  expect(await visit.evaluate((el) => el.contains(document.activeElement))).toBe(true);
  await page.keyboard.press('Escape'); await expect(visit).not.toBeVisible(); await expect(page.getByRole('heading', { name: 'Technician visit confirmed', exact: true })).not.toBeVisible();
  await page.reload(); await expect(visit).toBeVisible(); await page.keyboard.press('Escape'); await expect(page.locator('textarea')).toHaveCount(0);
  await selectDocument(page, { name: 'fictional-device.png', mimeType: 'image/png', buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=', 'base64') });
  await page.getByRole('button', { name: 'Upload document', exact: true }).click(); await expect(page.getByRole('link', { name: 'fictional-device.png', exact: true })).toBeVisible();
  await selectDocument(page, { name: 'case-invoice.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.7\nFictional case invoice') });
  await page.route(`**/api/complaints/${row.id}/documents`, route => route.request().method() === 'POST' ? route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ message: 'Temporary document failure' }) }) : route.continue());
  await page.getByRole('button', { name: 'Upload document', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Temporary document failure');
  await expect(page.getByText('case-invoice.pdf', { exact: true })).toBeVisible();
  await page.unroute(`**/api/complaints/${row.id}/documents`);
  await page.getByRole('button', { name: 'Upload document', exact: true }).click();
  await expect(page.getByRole('link', { name: 'case-invoice.pdf', exact: true })).toBeVisible();
  await expect(page.getByRole('img', { name: 'Stored case-invoice.pdf' })).toHaveCount(0);
  await page.reload(); await expect(visit).toBeVisible(); await page.keyboard.press('Escape');
  await expect(page.getByRole('img', { name: 'Stored fictional-device.png' })).toHaveJSProperty('naturalWidth', 1);
  await page.getByRole('button', { name: 'Confirm technician visit', exact: true }).click(); await visit.getByRole('button', { name: 'Confirm visit', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Technician visit confirmed', exact: true })).toBeVisible();
  expect((await (await page.request.get(`/api/complaints/${row.id}`)).json()).appointment.slotId).toBe(row.preferredSlotId);
  await page.reload(); await expect(page.getByRole('heading', { name: 'Technician visit confirmed', exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('conversation.png'), fullPage: true });
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Home', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Next technician visit', exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('home.png'), fullPage: true });
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Products', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Continue where you left off' })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('products.png'), fullPage: true });
  await page.getByRole('link', { name: 'Fictional Phone', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Current complaint', exact: true })).toBeVisible();
  await expect(page.getByText('View ongoing complaint', { exact: true })).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath('product-details.png'), fullPage: true });
  await page.goto(`/complaints/${row.id}`);
  await expect(page.getByRole('heading', { name: 'Technician visit confirmed' })).toBeVisible();
  const resolved = page.getByRole('checkbox', { name: 'The issue has been resolved.' });
  await expect(resolved).toHaveCSS('width', '20px'); await expect(resolved).toHaveCSS('height', '20px');
  await resolved.check(); await page.screenshot({ path: testInfo.outputPath('resolution-checkbox.png') });
  await page.getByRole('button', { name: 'Confirm issue resolved', exact: true }).click();
  await expect(page.getByText('Closed after your confirmation.')).toBeVisible();
  await expect(page.getByText('This chat is closed.', { exact: false })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Add document', exact: true })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Case photos', exact: true })).toHaveCount(0);
  await expect(page.locator('.conversation')).toHaveAttribute('data-read-only', 'true');
  await expect(page.getByRole('link', { name: 'Start a new complaint', exact: true })).toHaveAttribute('href', `/complaints/new?productId=${row.productId}`);
  expect((await page.request.post(`/api/complaints/${row.id}/documents`, { multipart: { file: { name: 'late.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.7\nLate document') } } })).status()).toBe(409);
  await page.reload(); await expect(page.getByText('This chat is closed.', { exact: false })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('closed-chat.png'), fullPage: true });
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Complaints', exact: true }).click(); await page.getByRole('button', { name: 'Past', exact: true }).click();
  await expect(page.getByText('Resolved', { exact: true })).toBeVisible();
  await page.getByLabel('Profile menu', { exact: true }).click(); await page.getByRole('link', { name: 'Addresses', exact: true }).click(); await expect(page.getByRole('heading', { name: 'Fictional home', exact: true })).toBeVisible(); await expect(page.getByText('Default', { exact: true })).toBeVisible();
  await page.getByLabel('Profile menu', { exact: true }).click(); await page.getByRole('link', { name: 'Profile', exact: true }).click();
  await page.route('**/api/auth/logout', (route) => route.abort('failed')); await page.getByRole('button', { name: 'Log out', exact: true }).click(); await expect(page.getByRole('alert')).toHaveText('Could not sign out. Check your connection and try again.');
  await page.unroute('**/api/auth/logout'); await page.getByRole('button', { name: 'Log out', exact: true }).click(); await expect(page.getByRole('heading', { name: 'Welcome to Custra' })).toBeVisible();
  expect(errors).toEqual([]); expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
});

test('model failure stops progress and explicit retry resumes', async ({ page, request }) => {
  await seedProduct(page); await openComplaintForm(page); await choosePreference(page); await request.post(`${controlsURL}/test/fail-model`);
  await page.getByRole('button', { name: 'Register complaint', exact: true }).click(); await expect(page.getByRole('button', { name: 'Retry saved step' })).toBeVisible();
  await expect(page.getByText('Custra is working on the next step…')).not.toBeVisible(); await page.getByRole('button', { name: 'Retry saved step' }).click();
  const visit = page.getByRole('dialog', { name: 'Confirm technician visit' }); await expect(visit).toBeVisible();
  await expect(visit.getByRole('button', { name: /Choose date|Change date/ })).toHaveCount(0);
  await visit.getByRole('button', { name: 'Confirm visit', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Technician visit confirmed', exact: true })).toBeVisible();
});

test('expired session returns to login', async ({ page, request }) => { await login(page); await request.post(`${controlsURL}/test/expire-session`); await page.reload(); await expect(page.getByRole('heading', { name: 'Welcome to Custra' })).toBeVisible(); });


test('first complaint completes missing profile inline without losing issue', async ({ page }) => {
  await login(page);
  const product = await (await page.request.post('/api/products', { data: { categoryId: 'smartphone', brandId: 'samsung', nickname: 'First phone' } })).json();
  await page.goto(`/complaints/new?productId=${product.id}`);
  await page.getByLabel('What’s wrong?', { exact: true }).fill('My fictional device will not start.');
  await page.getByRole('button', { name: 'Register complaint', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Contact details', exact: true });
  await expect(dialog).toBeVisible();
  await dialog.getByLabel('Full name', { exact: true }).fill('Fictional Customer');
  await dialog.getByLabel('Email', { exact: true }).fill('demo@example.test');
  await dialog.getByLabel('Phone number', { exact: true }).fill('0000000000');
  await dialog.getByRole('button', { name: 'Save details', exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByLabel('What’s wrong?', { exact: true })).toHaveValue('My fictional device will not start.');
  await page.getByRole('button', { name: 'Register complaint', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Confirm technician visit', exact: true })).toBeVisible();
});

test('failed optional invoice upload retries without duplicating product', async ({ page }) => {
  await login(page);
  await page.goto('/products/new');
  await page.getByLabel('Product type', { exact: true }).selectOption('smartphone');
  await page.getByLabel('Brand', { exact: true }).selectOption('samsung');
  await page.locator('#nickname').fill('Invoice retry phone');
  await page.getByRole('button', { name: 'Add document', exact: true }).click();
  const chooseFile = page.waitForEvent('filechooser');
  await page.getByRole('dialog', { name: 'Add document', exact: true }).getByRole('button', { name: 'Upload file', exact: true }).click();
  await (await chooseFile).setFiles({ name: 'invoice.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.7\nFictional') });
  await page.route('**/api/products/*/documents', (route) => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ message: 'Temporary upload failure' }) }));
  await page.getByRole('button', { name: 'Save product', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Product saved.');
  expect((await (await page.request.get('/api/products')).json())).toHaveLength(1);
  await page.unroute('**/api/products/*/documents');
  await page.getByRole('button', { name: 'Retry save', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Invoice retry phone', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'invoice.pdf', exact: true })).toBeVisible();
  expect((await (await page.request.get('/api/products')).json())).toHaveLength(1);
});

test('delete product closes linked complaints with history and survives retry', async ({ page, request }, testInfo) => {
  await seedProduct(page);
  const productId = page.url().split('/').at(-1);
  expect((await request.delete(`/api/products/${productId}`)).status()).toBe(401);
  await openComplaintForm(page); await choosePreference(page);
  await page.getByRole('button', { name: 'Register complaint', exact: true }).click();
  const visit = page.getByRole('dialog', { name: 'Confirm technician visit', exact: true }); await expect(visit).toBeVisible();
  await page.keyboard.press('Escape');
  const state = await (await request.get(`${controlsURL}/test/state`)).json(); const row = state.cases[0];
  await page.goto(`/products/${productId}`);
  await page.getByRole('button', { name: 'Delete product', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Delete product?', exact: true });
  await expect(dialog).toContainText('close');
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
  expect((await (await page.request.get(`/api/complaints/${row.id}`)).json()).status).toBe('AWAITING_APPOINTMENT');
  await page.getByRole('button', { name: 'Delete product', exact: true }).click();
  await page.screenshot({ path: testInfo.outputPath('delete-product.png') });
  await page.route(`**/api/products/${productId}`, route => route.request().method() === 'DELETE' ? route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ message: 'Temporary delete failure' }) }) : route.continue());
  await dialog.getByRole('button', { name: 'Delete product', exact: true }).click();
  await expect(dialog.getByRole('alert')).toContainText('Temporary delete failure');
  await page.unroute(`**/api/products/${productId}`);
  await dialog.getByRole('button', { name: 'Delete product', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Products', exact: true })).toBeVisible();
  expect((await (await page.request.get('/api/products')).json())).toHaveLength(0);
  expect((await page.request.get(`/api/products/${productId}`)).status()).toBe(404);
  const closed = await (await page.request.get(`/api/complaints/${row.id}`)).json();
  expect(closed.status).toBe('CLOSED'); expect(closed.closureReason).toBe('product_deleted'); expect(closed.resolvedAt).toBeUndefined();
  expect((await page.request.post(`/api/complaints/${row.id}/advance`, { data: { expectedVersion: row.currentVersion } })).status()).toBe(409);
  await page.goto(`/complaints/${row.id}`);
  await expect(page.getByText('Closed — product deleted', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Add document', exact: true })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Start a new complaint', exact: true })).toHaveAttribute('href', '/complaints/new');
  await expect(page.getByRole('button', { name: 'Confirm technician visit', exact: true })).toHaveCount(0);
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Complaints', exact: true }).click();
  await page.getByRole('button', { name: 'Past', exact: true }).click(); await expect(page.getByText('Closed — product deleted', { exact: true })).toBeVisible();
});
