/** Execute the real background entry point with strict k6 metric tags and no HTTP. */
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { comparisonPath } from '../../scripts/evaluation/k6/comparison_cases.js';
import { correctResponse, validSearchResponse } from '../../scripts/evaluation/k6/comparison_checks.js';
import { preliminaryOutcome } from '../../scripts/evaluation/k6/comparison_outcomes.js';
import { caseForIteration, validateComparisonCases, validateSequenceStarts } from '../../scripts/evaluation/k6/comparison_schedule.js';
const source = await readFile(new URL('../../scripts/evaluation/k6/nfr05_background.js', import.meta.url), 'utf8');
const caller = await readFile(new URL('../../scripts/evaluation/nfr05_browser.mjs', import.meta.url), 'utf8');
assert.match(caller, /CLIP_NFR05_BG_RUN_ID:\s*runId/);
// Keep this regression independent of private campaign inputs and execution history.
const id = '11111111-1111-4111-8111-111111111111';
const listing = { listing_id: id, title: 'Synthetic test item', description: 'Local test only', category_code: 'books', category_label: 'Books', condition_code: 'good', condition_label: 'Good', asking_price_paise: 10000, original_price_paise: null, negotiable: true, pickup_area: null, available_from: '2000-01-01T00:00:00.000000Z', available_until: null, availability: 'available', sensitive_purchase: false, image_ids: [id] };
const kinds = ['browse', 'search', 'detail', 'browse', 'search', 'browse', 'detail', 'search', 'browse', 'browse'];
const profile = {
  capacity: { preAllocatedVUs: 3, maxVUs: 3 }, timeout_seconds: 5,
  sequence_starts: { low: 0, normal: 1, burst: 2 },
  cases: kinds.map((kind, index) => ({
    case_id: `synthetic_${kind}_${index}`,
    request: kind === 'detail' ? { kind, listing_id: id } : { kind, query: { page: 1, page_size: 20, ...(kind === 'search' ? { q: 'synthetic', search_mode: 'hybrid' } : {}) } },
    expected: kind === 'detail' ? { ...listing, proof_available: null } : { items: [listing], page: 1, page_size: 20, has_next: false },
  })),
};
const transformed = source.replace(/^import .*;\n/gm, '').replace('export const options', 'const options').replace('export default function ()', 'globalThis.iteration = function ()');
function harness(runId) {
  const metrics = []; let reads = 0;
  const execution = { scenario: { name: 'nfr05_background', iterationInTest: 0 } };
  class Counter {
    constructor(name) { this.name = name; }
    add(value, tags = {}) {
      // Real k6 refuses undefined metric tags before issuing the HTTP request.
      for (const tag of Object.values(tags)) assert.ok(['string', 'boolean', 'number'].includes(typeof tag));
      metrics.push({ name: this.name, value, tags });
    }
  }
  const context = vm.createContext({ __ENV: { CLIP_NFR05_BG_EXECUTION: 'approved-runner', CLIP_NFR05_BG_TARGET_ORIGIN: 'https://synthetic.example.invalid', CLIP_NFR05_BG_SESSION_COOKIE: '__Host-clip_session=synthetic-local-no-auth', CLIP_NFR05_BG_RUN_ID: runId }, open: () => JSON.stringify(profile), Counter, execution, comparisonPath, correctResponse, validSearchResponse, preliminaryOutcome, caseForIteration, validateComparisonCases, validateSequenceStarts,
    http: { get(url) { reads++; const path = url.replace('https://synthetic.example.invalid/api', ''); const item = profile.cases.find(c => comparisonPath(c.request) === path); assert.ok(item); return { status: 200, error_code: 0, json: () => item.expected }; } } });
  vm.runInContext(transformed, context);
  return { context, execution, metrics, reads: () => reads };
}
assert.throws(() => harness(undefined), /nfr05_background_run_id_required/);
const h = harness('controlled-chat-background');
for (let i = 0; i < 20; i++) { h.execution.scenario.iterationInTest = i; h.context.iteration(); }
assert.equal(h.reads(), 20);
assert.equal(h.metrics.filter(r => r.name === 'clip_nfr05_bg_issued').length, 20);
assert.equal(h.metrics.filter(r => r.name === 'clip_nfr05_bg_outcomes' && r.tags.outcome === 'completed').length, 20);
assert.ok(h.metrics.every(r => r.tags.run_id === 'controlled-chat-background'));
h.execution.scenario.iterationInTest = 3000; h.context.iteration();
assert.equal(h.reads(), 20); assert.equal(h.metrics.at(-1).name, 'clip_nfr05_bg_boundary_skipped');
console.log('Actual background entry: 20 checked reads; missing run ID rejected; boundary issues no extra read; zero network actions.');
