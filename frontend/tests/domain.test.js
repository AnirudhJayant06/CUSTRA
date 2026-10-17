import test from 'node:test';
import assert from 'node:assert/strict';
import { warrantyStatus, sortCases, statusLabel } from '../src/lib/domain.js';
test('recorded warranty covers expiry day and missing data remains unknown', () => {
  assert.equal(warrantyStatus({}, '2026-10-17'), 'Warranty details missing');
  assert.equal(warrantyStatus({ warrantyExpiry: '2026-10-17' }, '2026-10-17'), 'Under warranty');
  assert.equal(warrantyStatus({ warrantyExpiry: '2026-10-16' }, '2026-10-17'), 'Out of warranty');
});
test('case sorting preserves input and display states do not expose enum names', () => {
  const source = [{ id: 'older', createdAt: '2026-10-16' }, { id: 'newer', createdAt: '2026-10-17' }];
  assert.deepEqual(sortCases(source).map((c) => c.id), ['newer', 'older']);
  assert.equal(source[0].id, 'older');
  assert.equal(statusLabel('AWAITING_APPOINTMENT'), 'Confirm visit');
  assert.equal(statusLabel('CLOSED', 'product_deleted'), 'Closed — product deleted');
  assert.equal(statusLabel('CLOSED'), 'Resolved');
});
