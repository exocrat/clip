import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

// Replace k6 APIs with local fakes; no network or workload is run.
function prepare({ throws = false, negative = false } = {}) {
  const source = readFileSync(new URL('./comparison_load.js', import.meta.url), 'utf8')
    .replace(/^import .*;$/gm, '')
    .replace('export const options', 'globalThis.options')
    .replace('export default function ()', 'globalThis.run = function ()');
  const recorded = {};
  let time = 100;
  class Metric {
    constructor(name) { this.name = name; recorded[name] = []; }
    add(value, tags) { recorded[this.name].push({ value, outcome: tags.outcome }); }
  }
  const item = { request: { kind: 'browse' }, expected: {} };
  const profile = { sequence_starts: { low: 0 }, cases: [item], capacity: { preAllocatedVUs: 1, maxVUs: 1 }, timeout_seconds: 5 };
  const context = {
    __ENV: { CLIP_COMPARISON_LOCAL_LOAD: 'true', CLIP_COMPARISON_LOCAL_COOKIE: 'synthetic', CLIP_COMPARISON_LOCAL_PROFILE: 'fixture', CLIP_COMPARISON_LOCAL_CONDITION: 'low' },
    open: () => JSON.stringify(profile), Date: { now: () => time }, Counter: Metric, Trend: Metric,
    localApiTarget: () => 'http://127.0.0.1', comparisonPath: () => '/synthetic',
    validateSequenceStarts: value => value, validateComparisonCases: value => value,
    validExpected: () => true, comparisonScenarios: () => ({}),
    execution: { scenario: { name: 'low_measured', iterationInTest: 0 } },
    sequenceStartForScenario: () => 0, caseForIteration: () => item,
    preliminaryOutcome: () => 'requires_correctness_check',
    correctResponse: () => { time += 500; return true; },
    http: { get: () => { time += negative ? -10 : 25; if (throws) throw Error('synthetic'); return { status: 200, json: () => ({}) }; } },
  };
  vm.runInNewContext(source, context);
  return { context, recorded };
}

test('elapsed time excludes response validation', () => {
  const { context, recorded } = prepare();
  context.run();
  assert.deepEqual(recorded.clip_comparison_elapsed_ms, [{ value: 25, outcome: 'correct' }]);
  assert.deepEqual(recorded.clip_comparison_outcomes, [{ value: 1, outcome: 'correct' }]);
});

test('thrown requests and negative clock samples remain accounted for', () => {
  const thrown = prepare({ throws: true });
  assert.throws(() => thrown.context.run());
  assert.deepEqual(thrown.recorded.clip_comparison_elapsed_ms, [{ value: 25, outcome: 'transport_error' }]);
  const negative = prepare({ negative: true });
  negative.context.run();
  assert.equal(negative.recorded.clip_comparison_elapsed_ms[0].value, 0);
  assert.equal(negative.recorded.clip_comparison_clock_invalid.length, 1);
});
