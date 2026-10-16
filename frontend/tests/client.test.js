import assert from 'node:assert/strict';
import test from 'node:test';

import { api, upload, ApiError } from '../src/api/client.js';

test('API client sends session cookie and JSON body', async () => {
  const original = globalThis.fetch;
  let options;
  globalThis.fetch = async (_url, passed) => {
    options = passed;
    return { ok: true, status: 200, json: async () => ({ saved: true }) };
  };
  try {
    const result = await api('/api/test', { method: 'POST', body: { name: 'Demo' } });
    assert.deepEqual(result, { saved: true });
    assert.equal(options.credentials, 'include');
    assert.equal(options.headers['Content-Type'], 'application/json');
    assert.equal(options.body, '{"name":"Demo"}');
  } finally {
    globalThis.fetch = original;
  }
});

test('API client exposes structured unauthorized error', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false, status: 401,
    json: async () => ({ code: 'unauthorized', message: 'Sign in to continue', retryable: false }),
  });
  try {
    await assert.rejects(() => api('/api/profile'), (error) =>
      error instanceof ApiError && error.status === 401 && error.code === 'unauthorized');
  } finally {
    globalThis.fetch = original;
  }
});

test('expired upload emits the session-expired event', async () => {
  const originalFetch = globalThis.fetch;
  const originalWindow = globalThis.window;
  const target = new EventTarget();
  let expired = false;
  target.addEventListener('custra:session-expired', () => { expired = true; });
  globalThis.window = target;
  globalThis.fetch = async () => ({ ok: false, status: 401,
    json: async () => ({ code: 'unauthorized', message: 'Sign in to continue' }) });
  try {
    await assert.rejects(() => upload('/api/products/fictional/documents', new FormData()), ApiError);
    assert.equal(expired, true);
  } finally {
    globalThis.fetch = originalFetch;
    if (originalWindow === undefined) delete globalThis.window;
    else globalThis.window = originalWindow;
  }
});
