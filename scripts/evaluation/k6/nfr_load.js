import { sha256 } from 'k6/crypto';
import { responseCorrelation } from './request_correlation.js';
// NFR-01/02 workload. Direct/local preparation stays loopback-only; a reviewed
// coordinator must validate every gate before using its separate real mode.
import http from 'k6/http';
import { localCapacityWindow } from './local_capacity_window.js';
import { plannedArrivalCount } from './core.js';
import execution from 'k6/execution';
import { Counter, Trend } from 'k6/metrics';
import monotonic from 'k6/x/clipmonotonic';
import { approvedApiTarget, localApiTarget, comparisonPath } from './comparison_cases.js';
import { preliminaryOutcome } from './comparison_outcomes.js';
import { successfulNfrResponse, nfrCaseForIteration, nfrScenarios, validateNfrProfile } from './nfr_workload.js';

const realMode = __ENV.CLIP_NFR_REAL_RUN_MODE === 'approved-runner';
if (realMode ? __ENV.CLIP_NFR_LOCAL_LOAD === 'true' : __ENV.CLIP_NFR_LOCAL_LOAD !== 'true') throw Error('explicit_load_runner_mode_required');
const target = realMode
  ? approvedApiTarget(__ENV.CLIP_NFR_REAL_TARGET, __ENV.CLIP_NFR_REAL_ORIGIN)
  : localApiTarget(__ENV.CLIP_NFR_LOCAL_TARGET);
const rawProfile = open(realMode ? __ENV.CLIP_NFR_REAL_PROFILE : __ENV.CLIP_NFR_LOCAL_PROFILE);
if (rawProfile.length > 5_000_000) throw Error('nfr_profile_too_large');
const profile = validateNfrProfile(JSON.parse(rawProfile));
const paths = profile.cases.map(item => comparisonPath(item.request));
// Read the synthetic session only after every workload input passes validation.
if (realMode && (!/^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$/.test(__ENV.CLIP_NFR_REAL_RUN_ID || '') || __ENV.CLIP_NFR_REAL_RUN_ID !== profile.run_id || __ENV.CLIP_NFR_REAL_CONFIGURATION !== profile.configuration)) throw Error('approved_run_binding_required');
const cookie = realMode ? __ENV.CLIP_REAL_RUN_SESSION_COOKIE : __ENV.CLIP_NFR_LOCAL_COOKIE;
if (typeof cookie !== 'string' || !cookie || /[\r\n]/.test(cookie)) throw Error('explicit_session_required');

const boundarySkipped = new Counter('clip_schedule_boundary_skipped');
const issued = new Counter('clip_nfr_issued');
const outcomes = new Counter('clip_nfr_outcomes');
const elapsed = new Trend('clip_nfr_elapsed_ms', true);
const invalidClock = new Counter('clip_nfr_clock_invalid');
const scenarios = nfrScenarios({ ...profile, ...localCapacityWindow(__ENV, realMode, profile) });
export const options = {
  scenarios,
  maxRedirects: 0,
  summaryTrendStats: ['med', 'p(95)', 'p(99)'],
  systemTags: ['scenario', 'status', 'method', 'error_code'],
};

/** Issue one non-retried request, validate its independent oracle, and retain only aggregate metrics. */
export default function () {
  const phase = execution.scenario.name;
  if (execution.scenario.iterationInTest >= plannedArrivalCount(scenarios[phase])) {
    boundarySkipped.add(1, { phase: execution.scenario.name });
    return;
  }
  const item = nfrCaseForIteration(profile.cases, execution.scenario.iterationInTest);
  const tags = { nfr_id: profile.nfr_id, configuration: profile.configuration, run_id: profile.run_id, phase, case_id: item.case_id };
  tags.sample_index = String(execution.scenario.iterationInTest);
  issued.add(1, tags);
  let outcome = 'transport_error';
  let duration;
  let timerStarted = false;
  try {
    monotonic.start();
    timerStarted = true;
    let response;
    try {
      response = http.get(`${target}${paths[profile.cases.indexOf(item)]}`, {
        headers: { Accept: 'application/json', 'Cache-Control': 'no-cache', Cookie: cookie },
        redirects: 0,
        timeout: `${profile.timeout_seconds}s`,
        tags,
      });
    } finally {
      duration = monotonic.stop();
      timerStarted = false;
    }
    Object.assign(tags, responseCorrelation(response, value => sha256(value, 'hex')));
    outcome = preliminaryOutcome(response);
    if (outcome === 'requires_correctness_check') {
      if (profile.nfr_id === 'nfr-02') {
        outcome = successfulNfrResponse(response.status, null, item, profile.nfr_id) ? 'completed' : 'http_error';
      } else {
        outcome = 'incorrect';
        try {
          if (successfulNfrResponse(response.status, response.json(), item, profile.nfr_id)) outcome = 'correct';
        } catch (_) { /* Never emit response bodies or parser details. */ }
      }
    }
  } finally {
    if (timerStarted) {
      try { duration = monotonic.stop(); } catch (_) { /* Missing sample is reported as invalid timing. */ }
    }
    if (!Number.isFinite(duration) || duration < 0) invalidClock.add(1, tags);
    else elapsed.add(duration, { ...tags, outcome });
    outcomes.add(1, { ...tags, outcome });
  }
}
