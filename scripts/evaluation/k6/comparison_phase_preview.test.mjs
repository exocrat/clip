import { test } from 'node:test';
import assert from 'node:assert/strict';
import { phaseTimingPreview } from './comparison_phase_preview.js';

test('previews paired per-request phases without adding connection subphases', () => {
  const timings = { blocked: 100, connecting: 40, tls_handshaking: 30, duration: 200 };
  assert.deepEqual(phaseTimingPreview({timings}, 'correct'), {
    eligible: true, request_ms: 200, approximate_span_ms: 300,
  });
  assert.equal(phaseTimingPreview({timings: {blocked: 0, duration: 150}}, 'correct').approximate_span_ms, 150);
});

test('refuses failures, invalid phases and spans above the approved timeout', () => {
  for (const outcome of ['timeout', 'transport_error', 'incorrect', 'throttled']) {
    assert.deepEqual(phaseTimingPreview({timings: {blocked: 0, duration: 0}}, outcome), {eligible: false, reason: 'not_correct'});
  }
  for (const timings of [null, {}, {blocked: -1, duration: 3}, {blocked: 1, duration: NaN}]) {
    assert.equal(phaseTimingPreview({timings}, 'correct').reason, 'invalid_phase');
  }
  assert.equal(phaseTimingPreview({timings: {blocked: 2, duration: 5000}}, 'correct').reason, 'implausible_span');
});
