import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { validateNfrDraft } from './nfr_profile_preflight.js';

const read = name => JSON.parse(readFileSync(new URL(`../../../data/evaluation/workloads/${name}`, import.meta.url)));
const browse = read('browse-nfr-draft-v1.json');
const hybrid = read('hybrid-nfr-draft-v1.json');
const syntheticId = '11111111-1111-4111-8111-111111111111';
const repaired = p => ({...p, warmup_seconds: 60, timeout_seconds: 5, cases: p.cases.map(c => ({...c, expected_ids: [syntheticId]}))});

test('refuses repository drafts and missing expected results without requests', () => {
  assert.throws(() => validateNfrDraft(browse, 'nfr-01'), /design_values_mismatch/);
  assert.throws(() => validateNfrDraft(hybrid, 'nfr-02'), /design_values_mismatch/);
  assert.throws(() => validateNfrDraft({...browse, warmup_seconds: 60, timeout_seconds: 5}, 'nfr-01'), /expected_ids_required/);
  const result = spawnSync(process.execPath, ['scripts/evaluation/k6/nfr_profile_preflight.mjs', 'nfr-01', 'data/evaluation/workloads/browse-nfr-draft-v1.json'], {encoding: 'utf8'});
  assert.equal(result.status, 2);
});

test('checks distinct rates and explicit Hybrid without claiming readiness', () => {
  for (const [profile, nfr] of [[repaired(browse), 'nfr-01'], [repaired(hybrid), 'nfr-02']]) {
    const result = validateNfrDraft(profile, nfr);
    assert.equal(result.execution_permitted, false);
    assert.equal(result.nfr_accepted, false);
    assert.equal(result.draft_shape_valid, true);
    assert.throws(() => validateNfrDraft({...profile, rate: 50}, nfr), /design_values_mismatch/);
    assert.throws(() => validateNfrDraft({...profile, cases: [{...profile.cases[0], expected_ids: null}]}, nfr), /expected_ids_required/);
  }
  const profile = repaired(hybrid);
  profile.cases[0].query.search_mode = 'keyword';
  assert.throws(() => validateNfrDraft(profile, 'nfr-02'), /invalid_search/);
});

test('rejects malformed case values and duplicate expected IDs', () => {
  const profile = repaired(browse);
  assert.throws(() => validateNfrDraft({...profile, cases: [{...profile.cases[0], query: {page: 0}}]}, 'nfr-01'), /invalid_query/);
  assert.throws(() => validateNfrDraft({...profile, cases: [{...profile.cases[0], expected_ids: [syntheticId, syntheticId]}]}, 'nfr-01'), /expected_ids_required/);
  assert.throws(() => validateNfrDraft({...profile, cases: [{...profile.cases[0], expected_ids: ['not-an-id']}]}, 'nfr-01'), /expected_ids_required/);
});
