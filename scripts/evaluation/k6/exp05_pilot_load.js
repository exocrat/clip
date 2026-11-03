// Candidate-weight pilot: 60-second 10-read/s warm-up, then 120 seconds at 50 read/s.
// Only the shared coordinator may set approved-runner inputs for a live target.
import http from 'k6/http';
import execution from 'k6/execution';
import { Counter, Trend } from 'k6/metrics';
import { sha256 } from 'k6/crypto';
import monotonic from 'k6/x/clipmonotonic';
import { approvedApiTarget, comparisonPath, localApiTarget } from './comparison_cases.js';
import { correctResponse, validExpected } from './comparison_checks.js';
import { preliminaryOutcome } from './comparison_outcomes.js';

const exact = (value, keys) => value !== null && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const realMode = __ENV.CLIP_EXP05_REAL_RUN_MODE === 'approved-runner';
if (realMode ? __ENV.CLIP_EXP05_LOCAL_LOAD === 'true' : __ENV.CLIP_EXP05_LOCAL_LOAD !== 'true') throw Error('explicit_pilot_runner_mode_required');
const target = realMode
  ? approvedApiTarget(__ENV.CLIP_EXP05_REAL_TARGET, __ENV.CLIP_EXP05_REAL_ORIGIN)
  : localApiTarget(__ENV.CLIP_EXP05_LOCAL_TARGET);
const profilePath = realMode ? __ENV.CLIP_EXP05_REAL_PROFILE : __ENV.CLIP_EXP05_LOCAL_PROFILE;
const rawProfile = open(profilePath);
if (rawProfile.length > 10_000_000) throw Error('pilot_profile_too_large');
const profile = JSON.parse(rawProfile);
const PROFILE_KEYS = ['version','purpose','run_id','configuration','dataset_fingerprint','case_bundle_sha256','workload_sha256','condition','rate_rps','warmup_rate_rps','warmup_seconds','measured_seconds','drain_seconds','timeout_seconds','retries','sequence_start','capacity','conditions','cases','execution_permitted','nfr_accepted'];
const workload = { dataset_fingerprint: profile.dataset_fingerprint, cases: profile.cases, sequence_start: profile.sequence_start, rate_rps: 50, warmup_rate_rps: 10, warmup_seconds: 60, measured_seconds: 120, timeout_seconds: 5, retries: 0, capacity: profile.capacity };
const canonical = value => {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value !== null && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
};
if (!exact(profile, PROFILE_KEYS) || profile.version !== 1 || profile.purpose !== 'exp05-pilot-workload' || profile.execution_permitted !== false || profile.nfr_accepted !== false || profile.condition !== 'burst' || profile.rate_rps !== 50 || profile.warmup_rate_rps !== 10 || profile.warmup_seconds !== 60 || profile.measured_seconds !== 120 || profile.drain_seconds !== 5 || profile.timeout_seconds !== 5 || profile.retries !== 0 || !Number.isSafeInteger(profile.sequence_start) || profile.sequence_start < 0 || profile.sequence_start > 9 || !exact(profile.capacity, ['preAllocatedVUs','maxVUs']) || !Number.isSafeInteger(profile.capacity.preAllocatedVUs) || !Number.isSafeInteger(profile.capacity.maxVUs) || profile.capacity.preAllocatedVUs < 1 || profile.capacity.maxVUs < profile.capacity.preAllocatedVUs || !Array.isArray(profile.cases) || profile.cases.length !== 10 || !Array.isArray(profile.conditions) || canonical(profile.conditions) !== canonical([{ name: 'burst', warmup_rate: 10, measured_rate: 50 }]) || sha256(canonical(profile.cases), 'hex') !== profile.case_bundle_sha256 || sha256(canonical(workload), 'hex') !== profile.workload_sha256) throw Error('pilot_profile_mismatch');
if (realMode && (profile.run_id !== __ENV.CLIP_EXP05_REAL_RUN_ID || profile.configuration !== __ENV.CLIP_EXP05_REAL_CONFIGURATION)) throw Error('pilot_run_binding_mismatch');
const cases = profile.cases;
const paths = cases.map(item => {
  const path = comparisonPath(item.request);
  if (!validExpected(item.request, item.expected)) throw Error('invalid_pilot_expected_case');
  return path;
});
const cookie = realMode ? __ENV.CLIP_REAL_RUN_SESSION_COOKIE : __ENV.CLIP_EXP05_LOCAL_COOKIE;
if (typeof cookie !== 'string' || !cookie || /[\r\n]/.test(cookie)) throw Error('pilot_session_required');
const scenarios = {
  burst_warmup: { executor: 'constant-arrival-rate', rate: 10, timeUnit: '1s', duration: '60s', startTime: '0s', preAllocatedVUs: profile.capacity.preAllocatedVUs, maxVUs: profile.capacity.maxVUs, gracefulStop: '5s' },
  burst_measured: { executor: 'constant-arrival-rate', rate: 50, timeUnit: '1s', duration: '120s', startTime: '65s', preAllocatedVUs: profile.capacity.preAllocatedVUs, maxVUs: profile.capacity.maxVUs, gracefulStop: '5s' },
};
const issued = new Counter('clip_comparison_issued');
const outcomes = new Counter('clip_comparison_outcomes');
const elapsed = new Trend('clip_comparison_elapsed_ms', true);
const invalidClock = new Counter('clip_comparison_clock_invalid');
export const options = { scenarios, maxRedirects: 0, summaryTrendStats: ['med','p(95)','p(99)'], systemTags: ['scenario','status','method','error_code'] };

/** Run exactly one expected, non-retried Listing read for each scheduled iteration. */
export default function () {
  const phase = execution.scenario.name;
  const iteration = execution.scenario.iterationInTest;
  const index = (profile.sequence_start + iteration) % cases.length;
  const item = cases[index];
  const tags = { phase, kind: item.request.kind, case_index: String(index), ...(realMode ? { run_id: profile.run_id, configuration: profile.configuration } : {}) };
  issued.add(1, tags);
  let outcome = 'transport_error';
  let duration;
  let timerStarted = false;
  try {
    monotonic.start(); timerStarted = true;
    let response;
    try {
      response = http.get(`${target}${paths[index]}`, { headers: { Accept: 'application/json', 'Cache-Control': 'no-cache', Cookie: cookie }, redirects: 0, timeout: '5s', tags });
    } finally { duration = monotonic.stop(); timerStarted = false; }
    outcome = preliminaryOutcome(response);
    if (outcome === 'requires_correctness_check') {
      outcome = 'incorrect';
      try { if (correctResponse(response.status, response.json(), item.request, item.expected)) outcome = 'correct'; }
      catch (_) { /* Record a fixed incorrect outcome; never retain response content. */ }
    }
  } finally {
    if (timerStarted) { try { duration = monotonic.stop(); } catch (_) { /* Invalid timing remains visible. */ } }
    if (!Number.isFinite(duration) || duration < 0) invalidClock.add(1, tags); else elapsed.add(duration, { ...tags, outcome });
    outcomes.add(1, { ...tags, outcome });
  }
}
