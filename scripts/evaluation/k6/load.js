import http from 'k6/http';
import exec from 'k6/execution';
import { Counter, Trend } from 'k6/metrics';
import { validateProfile, validPage, scenarios } from './core.js';

// Wrapper supplies exact local files/target. No remote module, auth/token, cloud
// export, redirect, retry, image body or extra request is hidden in an iteration.
const profile = validateProfile(JSON.parse(open(__ENV.CLIP_LOAD_PROFILE)));
if (profile.purpose !== 'local-pilot' || __ENV.CLIP_LOAD_ISOLATED !== 'true' || !/^http:\/\/127\.0\.0\.1:[0-9]+$/.test(__ENV.CLIP_LOAD_TARGET)) throw Error('local_pilot_only');
const issued = new Counter('clip_issued');
const elapsed = new Trend('clip_elapsed_ms', true);
const clockInvalid = new Counter('clip_clock_invalid');
const outsideCohort = new Counter('clip_outside_cohort');
export const options = { scenarios:scenarios(profile), maxRedirects:0, systemTags:['scenario','status','method','expected_response','error_code'], summaryTrendStats:['med','p(95)','p(99)'] };

/** One logical iteration is exactly one uncached HTTP request; outcome is never inferred from status alone. */
export default function () {
  const phase = exec.scenario.name;
  const slots = profile.rate * (phase === 'warmup' ? profile.warmup_seconds : profile.measured_seconds);
  // Some k6 schedules start an iteration on the exact end boundary. It is
  // outside this half-open arrival cohort; count it without exceeding HTTP caps.
  if (exec.scenario.iterationInTest >= slots) { outsideCohort.add(1,{phase}); return; }
  const item = profile.cases[exec.scenario.iterationInTest % profile.cases.length];
  const query = Object.entries(item.query).map(([key,value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`).join('&');
  const tags = {phase,case_id:item.id};
  issued.add(1,tags);
  let outcome = 'transport';
  const start = Date.now();
  try {
    const response = http.get(`${__ENV.CLIP_LOAD_TARGET}/listings${query ? `?${query}` : ''}`, {timeout:`${profile.timeout_seconds}s`,redirects:0,headers:{Accept:'application/json','Cache-Control':'no-cache','X-Clip-UI-Preview':'search-fixtures'},tags});
    if (response.error_code === 1050) outcome = 'timeout';
    else if ([401,403].includes(response.status)) outcome = 'unauthorized';
    else if (response.status !== 200) outcome = response.status === 0 ? 'transport' : 'http_error';
    else {
      outcome = 'invalid';
      try {
        if (validPage(response.json(),item) && response.headers['X-Clip-Preview'] === (__ENV.CLIP_LOAD_TARGET_KIND === 'native' ? 'search-native-model-synthetic-identity' : 'search-load-fault-fixtures') && response.headers['Cache-Control'] === 'private, no-store') outcome = 'ok';
      } catch (_) { /* Safe fixed outcome; never retain rejected response content. */ }
    }
  } finally {
    const duration = Date.now() - start;
    if (duration < 0) clockInvalid.add(1,tags);
    elapsed.add(Math.max(0,duration),{...tags,outcome});
  }
}

/** Completion marker avoids summary-schema assumptions; raw local metric points are authoritative. */
export function handleSummary() {
  return {[__ENV.CLIP_LOAD_FINISHED]: JSON.stringify({completed:true,preview_only:true,nfr_accepted:false})};
}
