import { test } from 'node:test';
import assert from 'node:assert/strict';
import { COHORT_SECONDS, caseForIteration, comparisonScenarios, sequenceStartForScenario, validateComparisonCases, validateSequenceStarts } from './comparison_schedule.js';

const kinds = ['browse','search','detail','browse','search','browse','detail','search','browse','browse'];
const cases = kinds.map((kind,index) => ({request:{kind},expected:{id:index}}));

test('each condition schedules only its own approved warm-up and measured cohorts', () => {
  const capacity = {preAllocatedVUs:2,maxVUs:4};
  const low = comparisonScenarios(capacity, 'low');
  const normal = comparisonScenarios(capacity, 'normal');
  const burst = comparisonScenarios(capacity, 'burst');
  assert.deepEqual(Object.keys(low), ['low_warmup','low_measured']);
  assert.deepEqual(Object.keys(normal), ['normal_warmup','normal_measured']);
  assert.deepEqual(Object.keys(burst), ['burst_warmup','burst_measured']);
  assert.deepEqual([low.low_measured.rate,low.low_measured.timeUnit,low.low_measured.duration], [1,'5s','300s']);
  assert.deepEqual([normal.normal_measured.rate,normal.normal_measured.timeUnit,normal.normal_measured.duration], [10,'1s','300s']);
  assert.deepEqual([burst.burst_warmup.rate,burst.burst_measured.rate], [10,50]);
  for (const [result, condition] of [[low,'low'], [normal,'normal'], [burst,'burst']]) {
    assert.equal(result[`${condition}_warmup`].startTime, '0s');
    assert.equal(result[`${condition}_warmup`].duration, '60s');
    assert.equal(result[`${condition}_measured`].gracefulStop, '5s');
  }
  assert.equal(low.low_measured.startTime, '65s');
  assert.equal(normal.normal_measured.startTime, '65s');
  assert.equal(burst.burst_measured.startTime, `${COHORT_SECONDS.warmup}s`);
  assert.throws(() => comparisonScenarios(null, 'low'), /capacity_required/);
  for (const condition of [undefined, null, 'all', 'LOW']) assert.throws(() => comparisonScenarios(capacity, condition), /condition_required/);
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
