import assert from 'node:assert/strict';
import test from 'node:test';
import { validWantedPage } from './nfr03_checks.js';
const item = index => ({ request_id: `20000000-0000-4000-8000-${String(index).padStart(12, '0')}`,
  title: 'Synthetic wanted fixture', description: 'Controlled fixture', category_code: 'other', category_label: 'Other',
  budget_paise: null, created_at: '2026-11-04T00:00:00.000000Z', updated_at: '2026-11-04T00:00:00.000000Z' });
test('accepts a correctly ordered page after new writes displace the initial fixture', () => {
  assert.ok(validWantedPage({ page: 1, page_size: 20, has_next: true,
    items: Array.from({length: 20}, (_, i) => item(100 - i)) }));
});
test('rejects duplicate, unordered, malformed and short-with-lookahead pages', () => {
  const page = items => ({ page: 1, page_size: 20, has_next: false, items });
  assert.equal(validWantedPage(page([item(1), item(2)])), false);
  assert.equal(validWantedPage(page([item(1), item(1)])), false);
  assert.equal(validWantedPage(page([{...item(1), title: ''}])), false);
  assert.equal(validWantedPage({...page([item(1)]), has_next: true}), false);
});
