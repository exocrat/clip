import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { validateNfrCases } from './nfr_cases_check.js';
import { correctResponse } from './comparison_checks.js';

const corpus = JSON.parse(readFileSync(new URL('../../../data/evaluation/workloads/ecs-lambda-case-corpus-v1.json', import.meta.url)));
const draft = () => ({format_version: 1, purpose: 'nfr-case-drafts-not-executable', execution_permitted: false, nfr_accepted: false,
  nfr_01: structuredClone(corpus.cases.filter(c => c.request.kind === 'browse')).map(c => ({...c, expected_status: 200})),
  nfr_02: structuredClone(corpus.cases.filter(c => c.request.kind === 'search')).map(c => ({...c, expected_status: 200})) });

test('validates browse expectations and accepts Hybrid latency inputs without rankings', () => {
  const previous = Date.now;
  Date.now = () => Date.parse('2026-11-01T00:00:00Z');
  try {
    const bundle = draft();
    assert.equal(validateNfrCases(bundle, 'nfr-01').execution_permitted, false);
    assert.equal(validateNfrCases(bundle, 'nfr-02').execution_permitted, false);
    const browse = bundle.nfr_01[0];
    const reversed = structuredClone(browse.expected);
    reversed.items.reverse();
    assert.equal(correctResponse(200, reversed, browse.request, browse.expected), false);
    const invalid = structuredClone(bundle);
    delete invalid.nfr_01[0].expected.items[0].title;
    assert.throws(() => validateNfrCases(invalid, 'nfr-01'), /missing_or_invalid_expected/);
    invalid.nfr_01[0].expected = structuredClone(bundle.nfr_01[0].expected);
    invalid.nfr_01[0].expected.page = 2;
    assert.throws(() => validateNfrCases(invalid, 'nfr-01'), /missing_or_invalid_expected/);
    const wrongFilter = structuredClone(bundle);
    wrongFilter.nfr_01[2].expected.items[0].category_code = 'books';
    assert.throws(() => validateNfrCases(wrongFilter, 'nfr-01'), /missing_or_invalid_expected/);
    const unavailable = structuredClone(bundle);
    unavailable.nfr_01[0].expected.items[0].availability = 'sold';
    assert.throws(() => validateNfrCases(unavailable, 'nfr-01'), /missing_or_invalid_expected/);
    const wrongStatus = structuredClone(bundle);
    wrongStatus.nfr_01[0].expected_status = 201;
    assert.throws(() => validateNfrCases(wrongStatus, 'nfr-01'), /invalid_case/);
  } finally { Date.now = previous; }
});

test('accepts synthetic Hybrid shapes without attesting review and checks classes', () => {
  const previous = Date.now;
  Date.now = () => Date.parse('2026-11-01T00:00:00Z');
  try {
    const bundle = draft();
    assert.equal(validateNfrCases(bundle, 'nfr-02').nfr_accepted, false);
    bundle.nfr_02[0].expected = structuredClone(bundle.nfr_01[0].expected);
    assert.throws(() => validateNfrCases(bundle, 'nfr-02'), /invalid_latency_search_case/);
    bundle.nfr_02[0].expected = null;
    bundle.nfr_02[0].relevance_reference.query_class = 'related_word';
    assert.throws(() => validateNfrCases(bundle, 'nfr-02'), /missing_query_classes/);
  } finally { Date.now = previous; }
});
