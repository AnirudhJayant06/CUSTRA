import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
const control = 'http://127.0.0.1:8018';
test.beforeEach(async ({ request }) => {
  test.skip(Boolean(process.env.CUSTRA_UI_URL), 'Fictional local fixture only');
  await request.post(`${control}/test/reset`);
});
async function setup(page, request, sharing = false) {
  const auth = JSON.parse(readFileSync('/tmp/custra-e2e-credentials.json', 'utf8'));
  await page.goto('/login');
  await page.getByLabel('Username', { exact: true }).fill(auth.username);
  await page.getByLabel('Password', { exact: true }).fill(auth.password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Active complaints', exact: true })).toBeVisible();
  await page.request.patch('/api/profile', { data: { name: 'Fiction User', phone: '9000000000', email: 'fiction@example.test' } });
  const product = await (await page.request.post('/api/products', { data: { categoryId: 'smartphone', brandId: 'samsung', modelNumber: 'WM-100', nickname: 'Knowledge Phone', ...(sharing ? { purchaseDate: '2026-02-12' } : {}) } })).json();
  expect((await request.post(`${control}/test/natural?request_document=${sharing}`)).ok()).toBeTruthy();
  const addresses = await (await page.request.get('/api/addresses')).json();
  const complaint = await (await page.request.post('/api/complaints', { headers: { 'Idempotency-Key': 'knowledge-test-key-1234' }, data: {
    productId: product.id, addressId: addresses[0].id, description: 'The fictional device stops.' } })).json();
  return { complaint, product };
}

test('natural registration hands off missing fact, restores it and books', async ({ page, request }, info) => {
  const { complaint, product } = await setup(page, request);
  await page.goto(`/complaints/${complaint.id}`);
  const input = page.getByLabel('Purchase date', { exact: true });
  await expect(input).toBeVisible(); await page.reload(); await expect(input).toBeVisible();
  await input.fill('2026-02-12'); await page.getByRole('button', { name: 'Send details', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Confirm technician visit', exact: true });
  await expect(dialog).toBeVisible(); await dialog.getByRole('button', { name: 'Confirm visit', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Technician visit confirmed', exact: true })).toBeVisible();
  const knowledge = await (await page.request.get(`/api/products/${product.id}/knowledge`)).json();
  expect(knowledge.facts['product.purchaseDate'].value).toBe('2026-02-12');
  await page.screenshot({ path: info.outputPath('knowledge-registration.png'), fullPage: true });
});

test('product upload is indexed, chat upload stays unindexed until promotion', async ({ page, request }) => {
  const { complaint, product } = await setup(page, request);
  const document = await (await page.request.post(`/api/products/${product.id}/documents`, { multipart: {
    file: { name: 'invoice.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.7 fictional invoice') } } })).json();
  expect(document.processingStatus).toBe('searchable');
  const chat = await (await page.request.post(`/api/complaints/${complaint.id}/documents`, { multipart: {
    file: { name: 'chat-invoice.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.7 chat invoice') } } })).json();
  expect(chat.processingStatus).toBeUndefined();
  let docs = await (await page.request.get(`/api/products/${product.id}/documents`)).json();
  expect(docs.some(d => d.id === chat.id)).toBe(false);
  expect((await page.request.post(`/api/complaints/${complaint.id}/documents/${chat.id}/save-to-product`)).ok()).toBe(true);
  docs = await (await page.request.get(`/api/products/${product.id}/documents`)).json();
  expect(docs.find(d => d.id === chat.id).processingStatus).toBe('searchable');
});

test('pause correction changes complaint phone and leaves Profile untouched', async ({ page, request }) => {
  const { complaint } = await setup(page, request);
  await page.goto(`/complaints/${complaint.id}`);
  await expect(page.getByLabel('Purchase date', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Pause and correct', exact: true }).click();
  await page.getByLabel('Information to correct', { exact: true }).selectOption('profile.phone');
  await page.getByLabel('Correct value', { exact: true }).fill('9111111111');
  await page.getByRole('button', { name: 'Save correction and continue', exact: true }).click();
  await expect(page.getByLabel('Purchase date', { exact: true })).toBeVisible();
  const saved = await (await page.request.get(`/api/complaints/${complaint.id}`)).json();
  expect(saved.factsSnapshot.profile.phone).toBe('9111111111');
  const profile = await (await page.request.get('/api/profile')).json();
  expect(profile.phone).toBe('9000000000');
});


test('business-requested invoice is selected and shared only after confirmation', async ({ page, request }, info) => {
  const { complaint, product } = await setup(page, request, true);
  const upload = await page.request.post(`/api/products/${product.id}/documents`, { multipart: {
    file: { name: 'saved-invoice.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.7 fictional invoice') } } });
  expect(upload.ok()).toBe(true);
  await page.goto(`/complaints/${complaint.id}`);
  await expect(page.getByRole('button', { name: 'Share this', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Choose another', exact: true })).toBeVisible();
  let saved = await (await page.request.get(`/api/complaints/${complaint.id}`)).json();
  expect(saved.status).toBe('AWAITING_USER');
  await page.screenshot({ path: info.outputPath('document-sharing.png'), fullPage: true });
  await page.getByRole('button', { name: 'Share this', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Confirm technician visit', exact: true })).toBeVisible();
  saved = await (await page.request.get(`/api/complaints/${complaint.id}`)).json();
  expect(saved.status).toBe('AWAITING_APPOINTMENT');
});

test('chat attachment answers missing detail and saving to Product Documents is optional', async ({ page, request }) => {
  const { complaint, product } = await setup(page, request);
  await page.goto(`/complaints/${complaint.id}`);
  await expect(page.getByLabel('Purchase date', { exact: true })).toBeVisible();
  const uploaded = await (await page.request.post(`/api/complaints/${complaint.id}/documents`, { multipart: {
    file: { name: 'chat-invoice.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.7 fictional invoice') } } })).json();
  await page.reload(); await page.getByRole('button', { name: 'Use this to answer', exact: true }).click();
  const visit = page.getByRole('dialog', { name: 'Confirm technician visit', exact: true });
  await expect(visit).toBeVisible(); await visit.getByRole('button', { name: 'Close', exact: true }).click();
  let documents = await (await page.request.get(`/api/products/${product.id}/documents`)).json();
  expect(documents).toHaveLength(0);
  await page.getByRole('button', { name: 'Save to product', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Save to product', exact: true })).toHaveCount(0);
  documents = await (await page.request.get(`/api/products/${product.id}/documents`)).json();
  expect(documents.find(d => d.id === uploaded.id).processingStatus).toBe('searchable');
});

test('manual retry budget survives refresh and stops after two retries', async ({ page, request }) => {
  const { complaint } = await setup(page, request);
  expect((await request.post(`${control}/test/fail-natural?count=3`)).ok()).toBe(true);
  await page.goto(`/complaints/${complaint.id}`);
  const retry = page.getByRole('button', { name: 'Retry saved step', exact: true });
  await expect(retry).toBeEnabled();
  const before = await (await page.request.get(`/api/complaints/${complaint.id}`)).json();
  await retry.click();
  await expect.poll(async () => (await (await page.request.get(`/api/complaints/${complaint.id}`)).json()).currentVersion).toBeGreaterThan(before.currentVersion);
  await expect(retry).toBeEnabled(); await page.reload();
  await expect(retry).toBeEnabled(); await retry.click();
  await expect(retry).toBeDisabled(); await page.reload();
  await expect(retry).toBeDisabled();
  await expect(page.getByRole('link', { name: 'Restart registration', exact: true })).toBeVisible();
});
