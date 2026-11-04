import { responseCorrelation } from './request_correlation.js';
import { createHash } from 'node:crypto';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { plannedArrivalCount } from './core.js';
import { localCapacityWindow } from './local_capacity_window.js';
const rules = {};
vm.runInNewContext(readFileSync(new URL('./nfr_workload.js', import.meta.url), 'utf8')
  .replace(/^import .*;$/gm, '').replace(/^export /gm, ''), rules);
const { nfrScenarios, nfrCaseForIteration } = rules;
import { preliminaryOutcome } from './comparison_outcomes.js';

// Execute the actual entry point with fake ports; emulate k6 rewriting its
// exported options in a VU. Internal scenario budgets must remain available.
function prepare(nfr = 'nfr-01') {
  const source = readFileSync(new URL('./nfr_load.js', import.meta.url), 'utf8')
    .replace(/^import .*;$/gm, '')
    .replace('export const options', 'globalThis.options')
    .replace('export default function ()', 'globalThis.run = function ()');
  const recorded = {};
  let calls = 0;
  class Metric {
    constructor(name) { this.name = name; recorded[name] = []; }
    add(value, tags) { recorded[this.name].push({ value, tags }); }
  }
  const profile = { nfr_id: nfr, configuration: 'A', run_id: 'synthetic-nfr', rate_rps: nfr === 'nfr-01' ? 20 : 10,
    warmup_seconds: 60, measured_seconds: 300, drain_seconds: 5, timeout_seconds: 5,
    capacity: { preAllocatedVUs: 1, maxVUs: 1 }, cases: [{case_id: 'synthetic', request: {kind: 'browse'}}] };
  const context = {
    responseCorrelation, sha256: value => createHash('sha256').update(value).digest('hex'),
    __ENV: { CLIP_NFR_LOCAL_LOAD: 'true', CLIP_NFR_LOCAL_COOKIE: 'synthetic', CLIP_NFR_LOCAL_PROFILE: 'fixture' },
    open: () => JSON.stringify(profile), Counter: Metric, Trend: Metric,
    localApiTarget: () => 'http://127.0.0.1', comparisonPath: () => '/fixture',
    validateNfrProfile: value => value, nfrScenarios, nfrCaseForIteration, preliminaryOutcome, plannedArrivalCount, localCapacityWindow,
    successfulNfrResponse: () => true,
    execution: {scenario: {name: 'nfr_measured', iterationInTest: 0}},
    monotonic: {start() {}, stop: () => 25},
    http: { get() { calls++; return {status: 200, error_code: 0, json() {
      if (nfr === 'nfr-02') throw Error('latency does not score JSON/ranking');
      return {};
    }}; } },
  };
  vm.runInNewContext(source, context);
  context.options.scenarios = {}; // Exported options are not request-time state.
  return {context, recorded, calls: () => calls};
}

test('browse still sends and measures after k6 rewrites exported options', () => {
  const check = prepare();
  check.context.run();
  assert.equal(check.calls(), 1);
  assert.equal(check.recorded.clip_nfr_outcomes[0].tags.outcome, 'correct');
  assert.equal(check.recorded.clip_nfr_elapsed_ms[0].value, 25);
});

test('search completion stays separate from ranking and boundary work is never issued', () => {
  const check = prepare('nfr-02');
  check.context.run();
  assert.equal(check.recorded.clip_nfr_outcomes[0].tags.outcome, 'completed');
  check.context.execution.scenario.iterationInTest = 3000;
  check.context.run();
  assert.equal(check.calls(), 1);
  assert.equal(check.recorded.clip_nfr_issued.length, 1);
  assert.equal(check.recorded.clip_schedule_boundary_skipped.length, 1);
});
