import { test } from 'node:test';
import assert from 'node:assert/strict';
import { COHORT_SECONDS, caseForIteration, comparisonScenarios, sequenceStartForScenario, validateComparisonCases, validateSequenceStarts } from './comparison_schedule.js';

const kinds = ['browse','search','detail','browse','search','browse','detail','search','browse','browse'];
const cases = kinds.map((kind,index) => ({request:{kind},expected:{id:index}}));

test('approved arrival cohorts keep low rate, warmup, burst transition and drain separate', () => {
  const result = comparisonScenarios({preAllocatedVUs:2,maxVUs:4});
  assert.deepEqual(Object.keys(result), ['low_warmup','low_measured','normal_warmup','normal_measured','burst_warmup','burst_measured']);
  assert.deepEqual([result.low_measured.rate,result.low_measured.timeUnit,result.low_measured.duration], [1,'5s','300s']);
  assert.deepEqual([result.normal_measured.rate,result.normal_measured.timeUnit,result.normal_measured.duration], [10,'1s','300s']);
  assert.deepEqual([result.burst_warmup.rate,result.burst_measured.rate], [10,50]);
  assert.equal(result.burst_measured.startTime, '800s');
  assert.equal(Number.parseInt(result.burst_measured.startTime,10), Number.parseInt(result.burst_warmup.startTime,10) + COHORT_SECONDS.warmup);
  assert.equal(result.normal_warmup.startTime, '370s');
  assert.throws(() => comparisonScenarios(null), /capacity_required/);
});

test('ten independently prepared cases enforce the approved 50/30/20 mix and rotate reproducibly', () => {
  assert.equal(validateComparisonCases(cases,3),cases);
  assert.equal(caseForIteration(cases,3,0),cases[3]);
  assert.equal(caseForIteration(cases,3,10),cases[3]);
  assert.throws(() => validateComparisonCases(cases.slice(1),0), /invalid_sequence/);
  assert.throws(() => validateComparisonCases([...cases.slice(0,9),{request:{kind:'search'},expected:{}}],0), /invalid_mix/);
});

test('each condition uses its own planned rotation for warm-up and measurement', () => {
  const starts = validateSequenceStarts({ low: 1, normal: 3, burst: 8 });
  for (const [condition, expected] of Object.entries(starts)) {
    for (const cohort of ['warmup', 'measured']) {
      const offset = sequenceStartForScenario(starts, `${condition}_${cohort}`);
      assert.equal(offset, expected);
      assert.equal(caseForIteration(cases, offset, 0), cases[expected]);
      assert.equal(caseForIteration(cases, offset, 10), cases[expected]);
    }
  }
  for (const invalid of [null, [], { low: 0, normal: 1 }, { low: 0, normal: 1, burst: 10 }, { low: 0, normal: 1, burst: true }, { low: 0, normal: 1, burst: 2, extra: 3 }]) {
    assert.throws(() => validateSequenceStarts(invalid), /invalid_sequence_starts/);
  }
  assert.throws(() => sequenceStartForScenario(starts, 'low_unknown'), /invalid_scenario/);
});
