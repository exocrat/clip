// EXP-02 scheduled workload. The separate real-target path is only an internal
// handoff; this script does not authorize a deployed run or an NFR result.
import http from 'k6/http';
import { plannedArrivalCount } from './core.js';
import execution from 'k6/execution';
import { Counter, Trend } from 'k6/metrics';
import monotonic from 'k6/x/clipmonotonic';
import { approvedApiTarget, comparisonPath, localApiTarget } from './comparison_cases.js';
import { correctResponse, correctParityDraftResponse, validExpected } from './comparison_checks.js';
import { checkAllParity } from './comparison_all_parity.js';
import { caseForIteration, comparisonScenarios, sequenceStartForScenario, validateComparisonCases, validateSequenceStarts } from './comparison_schedule.js';
import { preliminaryOutcome } from './comparison_outcomes.js';

const realMode = __ENV.CLIP_REAL_RUN_MODE === 'approved-runner';
const target = realMode
  ? approvedApiTarget(__ENV.CLIP_REAL_RUN_TARGET, __ENV.CLIP_REAL_RUN_ORIGIN)
  : localApiTarget(__ENV.CLIP_COMPARISON_LOCAL_TARGET);
if (realMode ? __ENV.CLIP_COMPARISON_LOCAL_LOAD === 'true' : __ENV.CLIP_COMPARISON_LOCAL_LOAD !== 'true') throw Error('explicit_load_runner_mode_required');
const profile = JSON.parse(open(realMode ? __ENV.CLIP_REAL_RUN_PROFILE : __ENV.CLIP_COMPARISON_LOCAL_PROFILE));
if (realMode && (!/^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$/.test(__ENV.CLIP_REAL_RUN_ID || '') || !['A', 'B'].includes(__ENV.CLIP_REAL_RUN_CONFIGURATION) || !['low', 'normal', 'burst'].includes(__ENV.CLIP_REAL_RUN_CONDITION))) throw Error('approved_run_binding_required');
const parityMode = !realMode && __ENV.CLIP_COMPARISON_LOCAL_PARITY_DRAFT === 'true';
const sequenceStarts = validateSequenceStarts(profile.sequence_starts);
const cases = validateComparisonCases(profile.cases, sequenceStarts.low);
if (!Number.isSafeInteger(profile.capacity?.preAllocatedVUs) || !Number.isSafeInteger(profile.capacity?.maxVUs) || !Number.isFinite(profile.timeout_seconds) || profile.timeout_seconds !== 5) throw Error('approved_capacity_and_timeout_required');
const paths = cases.map(item => {
  const path = comparisonPath(item.request);
  if (parityMode && item.request.kind === 'search' ? item.expected !== null : !validExpected(item.request, item.expected)) throw Error('invalid_expected_case');
  return path;
});
const condition = realMode ? __ENV.CLIP_REAL_RUN_CONDITION : __ENV.CLIP_COMPARISON_LOCAL_CONDITION;
const scenarios = comparisonScenarios(profile.capacity, condition);
if (parityMode) {
  const parityPath = __ENV.CLIP_COMPARISON_LOCAL_PARITY_FILE;
  if (typeof parityPath !== 'string' || !parityPath) throw Error('local_parity_input_required');
  try {
    const rawParity = open(parityPath);
    if (rawParity.length > 5_000_000) throw Error('local_parity_input_too_large');
    const parity = checkAllParity(JSON.parse(rawParity), {cases});
    if (!parity.all_equal_and_valid) throw Error('local_parity_mismatch');
  } catch (_) { throw Error('local_parity_invalid_or_mismatch'); }
}
// Do not read even the local session until profile, case and schedule checks pass.
const cookie = realMode ? __ENV.CLIP_REAL_RUN_SESSION_COOKIE : __ENV.CLIP_COMPARISON_LOCAL_COOKIE;
if (typeof cookie !== 'string' || !cookie || /[\r\n]/.test(cookie)) throw Error('explicit_local_load_inputs_required');

const boundarySkipped = new Counter('clip_schedule_boundary_skipped');
const issued = new Counter('clip_comparison_issued');
const outcomes = new Counter('clip_comparison_outcomes');
const elapsed = new Trend('clip_comparison_elapsed_ms', true);
const invalidClock = new Counter('clip_comparison_clock_invalid');
export const options = {
  scenarios,
  maxRedirects: 0,
  summaryTrendStats: ['med', 'p(95)', 'p(99)'],
  systemTags: ['scenario', 'status', 'method', 'error_code'],
};

/** A scheduled iteration performs exactly one checked, non-retried read. */
export default function () {
  const phase = execution.scenario.name;
  const iteration = execution.scenario.iterationInTest;
  if (execution.scenario.iterationInTest >= plannedArrivalCount(scenarios[phase])) {
    boundarySkipped.add(1, { phase: execution.scenario.name });
    return;
  }
  const sequenceStart = sequenceStartForScenario(sequenceStarts, phase);
  const item = caseForIteration(cases, sequenceStart, iteration);
  const index = (sequenceStart + iteration) % cases.length;
  const tags = { phase, kind: item.request.kind, case_index: String(index), ...(realMode ? { run_id: __ENV.CLIP_REAL_RUN_ID, configuration: __ENV.CLIP_REAL_RUN_CONFIGURATION } : {}) };
  issued.add(1, tags);
  let outcome = 'transport_error';
  let duration;
  let timerStarted = false;
  try {
    monotonic.start();
    timerStarted = true;
    let response;
    try {
      response = http.get(`${target}${paths[index]}`, {
        headers: { Accept: 'application/json', 'Cache-Control': 'no-cache', Cookie: cookie },
        redirects: 0,
        timeout: `${profile.timeout_seconds}s`,
        tags,
      });
    } finally {
      // Stop the elapsed-time clock on return or throw, before response checks.
      duration = monotonic.stop();
      timerStarted = false;
    }
    outcome = preliminaryOutcome(response);
    if (outcome === 'requires_correctness_check') {
      outcome = 'incorrect';
      try {
        const body = response.json();
        if (parityMode ? correctParityDraftResponse(response.status, body, item) : correctResponse(response.status, body, item.request, item.expected)) outcome = 'correct';
      }
      catch (_) { /* Malformed response content is counted without being retained. */ }
    }
  } finally {
    if (timerStarted) {
      try {
        duration = monotonic.stop();
      } catch (_) { /* Preserve the invalid timing as a missing latency sample. */ }
    }
    if (!Number.isFinite(duration) || duration < 0) invalidClock.add(1, tags);
    else elapsed.add(duration, { ...tags, outcome });
    outcomes.add(1, { ...tags, outcome });
  }
}
