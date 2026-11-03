import { test } from 'node:test';
import assert from 'node:assert/strict';
import { preliminaryOutcome } from './comparison_outcomes.js';

test('classifies request and connection timeouts without promoting other failures', () => {
  assert.equal(preliminaryOutcome({status: 0, error_code: 1050}), 'timeout');
  assert.equal(preliminaryOutcome({status: 0, error_code: 1211}), 'timeout');
  assert.equal(preliminaryOutcome({status: 0, error_code: 1212}), 'transport_error');
  assert.equal(preliminaryOutcome({status: 429}), 'throttled');
  assert.equal(preliminaryOutcome({status: 401}), 'unauthorized');
  assert.equal(preliminaryOutcome({status: 403}), 'unauthorized');
  assert.equal(preliminaryOutcome({status: 500}), 'http_error');
  assert.equal(preliminaryOutcome({status: 200}), 'requires_correctness_check');
});
