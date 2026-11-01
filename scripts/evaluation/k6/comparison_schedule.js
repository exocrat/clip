/** Approved EXP-01 timing and mix, expressed as one request per iteration. */
export const COMPARISON_PHASES = [
  { name: 'low', measuredRate: 1, timeUnit: '5s', warmupRate: 1, warmupTimeUnit: '5s' },
  { name: 'normal', measuredRate: 10, timeUnit: '1s', warmupRate: 10, warmupTimeUnit: '1s' },
  { name: 'burst', measuredRate: 50, timeUnit: '1s', warmupRate: 10, warmupTimeUnit: '1s' },
];

export const COHORT_SECONDS = { warmup: 60, measured: 300, drain: 5 };
export const MIX_COUNTS = { browse: 5, search: 3, detail: 2 };

/** Build six arrival cohorts; burst starts immediately while warm-up requests may drain.
 * VU capacity is per scenario, so burst overlap may use both scenarios' VUs.
 */
export function comparisonScenarios(capacity) {
  if (!Number.isSafeInteger(capacity?.preAllocatedVUs) || !Number.isSafeInteger(capacity?.maxVUs) || capacity.preAllocatedVUs < 1 || capacity.maxVUs < capacity.preAllocatedVUs) throw Error('capacity_required');
  let start = 0;
  const scenarios = {};
  for (const phase of COMPARISON_PHASES) {
    const add = (cohort, rate, timeUnit, duration) => {
      const name = `${phase.name}_${cohort}`;
      scenarios[name] = {
        executor: 'constant-arrival-rate',
        rate,
        timeUnit,
        duration: `${duration}s`,
        startTime: `${start}s`,
        preAllocatedVUs: capacity.preAllocatedVUs,
        maxVUs: capacity.maxVUs,
        gracefulStop: `${COHORT_SECONDS.drain}s`,
      };
      // The approved burst changes rate at the warm-up boundary. Its in-flight
      // warm-up requests keep their own scenario tag while allowed to drain.
      const immediateBurstTransition = phase.name === 'burst' && cohort === 'warmup';
      start += duration + (immediateBurstTransition ? 0 : COHORT_SECONDS.drain);
    };
    add('warmup', phase.warmupRate, phase.warmupTimeUnit, COHORT_SECONDS.warmup);
    add('measured', phase.measuredRate, phase.timeUnit, COHORT_SECONDS.measured);
  }
  return scenarios;
}

/** Check the ten-request rotation contract; the actual reviewed cases remain an input. */
export function validateComparisonCases(cases, sequenceStart) {
  if (!Array.isArray(cases) || cases.length !== 10 || !Number.isSafeInteger(sequenceStart) || sequenceStart < 0 || sequenceStart >= 10) throw Error('invalid_sequence');
  const counts = { browse: 0, search: 0, detail: 0 };
  for (const item of cases) {
    if (!item || !['browse', 'search', 'detail'].includes(item.request?.kind)) throw Error('invalid_case');
    counts[item.request.kind] += 1;
  }
  if (Object.keys(MIX_COUNTS).some(kind => counts[kind] !== MIX_COUNTS[kind])) throw Error('invalid_mix');
  return cases;
}

/** Stable cyclic rotation shared by matched A/B runs through the manifest's start index. */
export function caseForIteration(cases, sequenceStart, iteration) {
  if (!Number.isSafeInteger(iteration) || iteration < 0) throw Error('invalid_iteration');
  return cases[(sequenceStart + iteration) % cases.length];
}
