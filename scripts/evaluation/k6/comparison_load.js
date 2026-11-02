// EXP-02 scheduled comparison workload. Local API targets only; this is not an
// authorization to measure a deployment or an NFR result.
import http from 'k6/http';
import execution from 'k6/execution';
import { Counter, Trend } from 'k6/metrics';
import { comparisonPath, localApiTarget } from './comparison_cases.js';
import { correctResponse, validExpected } from './comparison_checks.js';
import { caseForIteration, comparisonScenarios, sequenceStartForScenario, validateComparisonCases, validateSequenceStarts } from './comparison_schedule.js';
import { preliminaryOutcome } from './comparison_outcomes.js';

const target = localApiTarget(__ENV.CLIP_COMPARISON_LOCAL_TARGET);
const cookie = __ENV.CLIP_COMPARISON_LOCAL_COOKIE;
if (__ENV.CLIP_COMPARISON_LOCAL_LOAD !== 'true' || typeof cookie !== 'string' || !cookie || /[\r\n]/.test(cookie)) throw Error('explicit_local_load_inputs_required');
const profile = JSON.parse(open(__ENV.CLIP_COMPARISON_LOCAL_PROFILE));
const sequenceStarts = validateSequenceStarts(profile.sequence_starts);
const cases = validateComparisonCases(profile.cases, sequenceStarts.low);
if (!Number.isSafeInteger(profile.capacity?.preAllocatedVUs) || !Number.isSafeInteger(profile.capacity?.maxVUs) || !Number.isFinite(profile.timeout_seconds) || profile.timeout_seconds !== 5) throw Error('approved_capacity_and_timeout_required');
const paths = cases.map(item => {
  const path = comparisonPath(item.request);
  if (!validExpected(item.request, item.expected)) throw Error('invalid_expected_case');
  return path;
});

const issued = new Counter('clip_comparison_issued');
const outcomes = new Counter('clip_comparison_outcomes');
const elapsed = new Trend('clip_comparison_elapsed_ms', true);
const invalidClock = new Counter('clip_comparison_clock_invalid');
export const options = {
  scenarios: comparisonScenarios(profile.capacity, __ENV.CLIP_COMPARISON_LOCAL_CONDITION),
  maxRedirects: 0,
  summaryTrendStats: ['med', 'p(95)', 'p(99)'],
  systemTags: ['scenario', 'status', 'method', 'error_code'],
};

/** A scheduled iteration performs exactly one checked, non-retried read. */
export default function () {
  const phase = execution.scenario.name;
  const iteration = execution.scenario.iterationInTest;
  const sequenceStart = sequenceStartForScenario(sequenceStarts, phase);
  const item = caseForIteration(cases, sequenceStart, iteration);
  const index = (sequenceStart + iteration) % cases.length;
  const tags = { phase, kind: item.request.kind, case_index: String(index) };
  issued.add(1, tags);
  const start = Date.now();
  let outcome = 'transport_error';
  let duration;
  try {
    let response;
    try {
      response = http.get(`${target}${paths[index]}`, {
        headers: { Accept: 'application/json', 'Cache-Control': 'no-cache', Cookie: cookie },
        redirects: 0,
        timeout: `${profile.timeout_seconds}s`,
        tags,
      });
    } finally {
      // Stop timing on return or throw, before interpreting the response.
      duration = Date.now() - start;
    }
    outcome = preliminaryOutcome(response);
    if (outcome === 'requires_correctness_check') {
      outcome = 'incorrect';
      try { if (correctResponse(response.status, response.json(), item.request, item.expected)) outcome = 'correct'; }
      catch (_) { /* Malformed response content is counted without being retained. */ }
    }
  } finally {
    if (duration < 0) invalidClock.add(1, tags);
    elapsed.add(Math.max(0, duration), { ...tags, outcome });
    outcomes.add(1, { ...tags, outcome });
  }
}
