// Bounded loopback-only k6 preparation. It is not an NFR or A/B run.
// The caller supplies a local session out of band; never print or record it.
import http from 'k6/http';
import execution from 'k6/execution';
import { Counter } from 'k6/metrics';
import { comparisonPath, localApiTarget } from './comparison_cases.js';
import { validExpected, correctResponse } from './comparison_checks.js';

const target = __ENV.CLIP_COMPARISON_LOCAL_TARGET;
const cookie = __ENV.CLIP_COMPARISON_LOCAL_COOKIE;
localApiTarget(target);
if (typeof cookie !== 'string' || !cookie || /[\r\n]/.test(cookie)) throw Error('invalid_session');
const cases = JSON.parse(__ENV.CLIP_COMPARISON_LOCAL_CASES || 'null');
if (!Array.isArray(cases) || cases.length < 1 || cases.length > 10) throw Error('local_case_limit');
const paths = cases.map(item => {
  if (!item || Object.keys(item).length !== 2 || !Object.hasOwn(item,'request') || !Object.hasOwn(item,'expected')) throw Error('invalid_case_envelope');
  const path = comparisonPath(item.request);
  if (!validExpected(item.request,item.expected)) throw Error('invalid_expected');
  return path;
});
const issued = new Counter('clip_comparison_preparation_issued');
const responses = new Counter('clip_comparison_preparation_response');

// Exactly one attempt per case; response bodies stay in memory and are not logged.
export const options = { vus: 1, iterations: cases.length, maxRedirects: 0, discardResponseBodies: false };

/** Issue one local request and compare it with the supplied expected content. */
export default function () {
  const index = execution.scenario.iterationInTest;
  if (!Number.isSafeInteger(index) || index < 0 || index >= cases.length) throw Error('invalid_iteration');
  const {request, expected} = cases[index];
  const tags = { kind: request.kind, case_index: String(index) };
  issued.add(1, tags);
  const response = http.get(`${target}${paths[index]}`, {
    headers: { Accept: 'application/json', 'Cache-Control': 'no-cache', Cookie: cookie },
    redirects: 0,
    timeout: '5s',
    tags,
  });
  let outcome = 'incorrect';
  if (response.status === 0) outcome = 'transport_error';
  else {
    try { if (correctResponse(response.status,response.json(),request,expected)) outcome = 'correct'; }
    catch (_) { /* Treat malformed JSON as incorrect without recording it. */ }
  }
  responses.add(1, { ...tags, outcome });
}
