// NFR-05's bounded normal browse-read background stream.
// The approved Node harness binds the target, profile, session and raw output.
import http from 'k6/http';
import execution from 'k6/execution';
import { Counter } from 'k6/metrics';
import { comparisonPath } from './comparison_cases.js';
import { preliminaryOutcome } from './comparison_outcomes.js';
import { correctResponse, validSearchResponse } from './comparison_checks.js';
import { caseForIteration, validateComparisonCases, validateSequenceStarts } from './comparison_schedule.js';

if (__ENV.CLIP_NFR05_BG_EXECUTION !== 'approved-runner') throw Error('approved_nfr05_runner_required');
const origin = __ENV.CLIP_NFR05_BG_TARGET_ORIGIN;
if (typeof origin !== 'string' || !/^https:\/\/[A-Za-z0-9.-]+(?::443)?$/.test(origin)) throw Error('approved_https_origin_required');
const target = `${origin.replace(/:443$/, '')}/api`;
const rawProfile = open(__ENV.CLIP_NFR05_BG_PROFILE);
if (rawProfile.length > 5_000_000) throw Error('nfr05_profile_too_large');
const profile = JSON.parse(rawProfile);
if (!profile || Object.keys(profile).sort().join(',') !== 'capacity,cases,sequence_starts,timeout_seconds' || profile.timeout_seconds !== 5 || !Number.isSafeInteger(profile.capacity?.preAllocatedVUs) || !Number.isSafeInteger(profile.capacity?.maxVUs) || profile.capacity.preAllocatedVUs < 1 || profile.capacity.maxVUs < profile.capacity.preAllocatedVUs) throw Error('nfr05_background_profile_mismatch');
const sequenceStarts = validateSequenceStarts(profile.sequence_starts);
validateComparisonCases(profile.cases, sequenceStarts.burst);
const paths = profile.cases.map(item => comparisonPath(item.request));
const runId = __ENV.CLIP_NFR05_BG_RUN_ID;
if (typeof runId !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$/.test(runId)) throw Error('nfr05_background_run_id_required');
const cookie = __ENV.CLIP_NFR05_BG_SESSION_COOKIE;
if (typeof cookie !== 'string' || !/^__Host-clip_session=[A-Za-z0-9._~+/=-]{1,2048}$/.test(cookie)) throw Error('nfr05_background_session_required');

const issued = new Counter('clip_nfr05_bg_issued');
const outcomes = new Counter('clip_nfr05_bg_outcomes');
const boundarySkipped = new Counter('clip_nfr05_bg_boundary_skipped');
export const options = {
  scenarios: {
    nfr05_background: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '300s',
      startTime: '0s',
      preAllocatedVUs: profile.capacity.preAllocatedVUs,
      maxVUs: profile.capacity.maxVUs,
      gracefulStop: '5s',
    },
  },
  maxRedirects: 0,
  systemTags: ['scenario', 'status', 'method', 'error_code'],
};

/** Send one authenticated, non-retried Hybrid search at each scheduled arrival. */
export default function () {
  const phase = execution.scenario.name;
  // k6 may schedule one boundary iteration; it must not add an unplanned read.
  if (execution.scenario.iterationInTest >= 3000) { boundarySkipped.add(1); return; }
  const item = caseForIteration(profile.cases, sequenceStarts.burst, execution.scenario.iterationInTest);
  const tags = { run_id: runId, phase, case_id: item.case_id };
  issued.add(1, tags);
  let outcome = 'transport_error';
  try {
    const response = http.get(`${target}${paths[profile.cases.indexOf(item)]}`, {
      headers: { Accept: 'application/json', 'Cache-Control': 'no-cache', Cookie: cookie },
      redirects: 0,
      timeout: '5s',
      tags,
    });
    outcome = preliminaryOutcome(response);
    if (outcome === 'requires_correctness_check') {
      outcome = 'incorrect';
      try {
        const body = response.json();
        if (item.request.kind === 'search'
          ? validSearchResponse(response.status, body, item.request)
          : correctResponse(response.status, body, item.request, item.expected)) outcome = 'completed';
      } catch (_) { /* Keep only the fixed outcome label. */ }
    }
  } catch (_) {
    outcome = 'transport_error';
  }
  outcomes.add(1, { ...tags, outcome });
}
