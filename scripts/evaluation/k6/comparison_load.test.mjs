import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { preliminaryOutcome } from './comparison_outcomes.js';

// Replace k6 APIs with local fakes; no network or workload is run.
function prepare({ throws = false, negative = false, timeout = false } = {}) {
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
    preliminaryOutcome,
    correctResponse: () => { time += 500; return true; },
    http: { get: () => { time += negative ? -10 : 25; if (throws) throw Error('synthetic'); if (timeout) return { status: 0, error_code: 1050 }; return { status: 200, json: () => ({}) }; } },
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

test('a returned timeout is recorded as a failure with its elapsed time', () => {
  const { context, recorded } = prepare({ timeout: true });
  context.run();
  assert.deepEqual(recorded.clip_comparison_elapsed_ms, [{ value: 25, outcome: 'timeout' }]);
  assert.deepEqual(recorded.clip_comparison_outcomes, [{ value: 1, outcome: 'timeout' }]);
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

test('invalid setup is refused before reading the local session', () => {
  const source = readFileSync(new URL('./comparison_load.js', import.meta.url), 'utf8')
    .replace(/^import .*;$/gm, '')
    .replace('export const options', 'globalThis.options')
    .replace('export default function ()', 'globalThis.run = function ()');
  for (const invalid of ['load_flag','sequence','cases','path','expected','capacity','scenario']) {
    let cookieReads=0;
    const env={CLIP_COMPARISON_LOCAL_LOAD:invalid==='load_flag'?'false':'true',CLIP_COMPARISON_LOCAL_PROFILE:'fixture',CLIP_COMPARISON_LOCAL_CONDITION:'low'};
    Object.defineProperty(env,'CLIP_COMPARISON_LOCAL_COOKIE',{get(){cookieReads++; return 'synthetic';}});
    const fail = name => { if (invalid===name) throw Error(`invalid_${name}`); };
    const profile={sequence_starts:{low:0},cases:[{request:{kind:'browse'},expected:{}}],capacity:{preAllocatedVUs:1,maxVUs:1},timeout_seconds:invalid==='capacity'?4:5};
    class Metric { add() {} }
    const context={__ENV:env,open:()=>JSON.stringify(profile),localApiTarget:()=> 'http://127.0.0.1',
      validateSequenceStarts:value=>{fail('sequence'); return value;},
      validateComparisonCases:value=>{fail('cases'); return value;},
      comparisonPath:()=>{fail('path'); return '/synthetic';},
      validExpected:()=>invalid!=='expected',comparisonScenarios:()=>{fail('scenario'); return {};},
      Counter:Metric,Trend:Metric};
    assert.throws(()=>vm.runInNewContext(source,context));
    assert.equal(cookieReads,0,invalid);
  }
});
