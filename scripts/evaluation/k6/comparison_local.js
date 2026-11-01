import { comparisonPath, localApiTarget } from './comparison_cases.js';

/** Send one local preparation request with an externally supplied session.
 * The injected transport receives the session in memory; callers must not log it.
 * The response is returned for later correctness checks, not declared successful.
 */
export async function sendLocalCase({ target, item, sessionCookie, send }) {
  localApiTarget(target);
  if (typeof sessionCookie !== 'string' || !sessionCookie || /[\r\n]/.test(sessionCookie) || typeof send !== 'function') throw Error('invalid_session_or_transport');
  const path = comparisonPath(item);
  return send(`${target}${path}`, {
    method: 'GET',
    headers: { Accept: 'application/json', 'Cache-Control': 'no-cache', Cookie: sessionCookie },
    redirect: 'error',
  });
}

/** Run a small sequential local preparation batch; never interpret status as correctness.
 * The transport and session are supplied by the caller and are not persisted.
 * Stop at the first transport failure so a partial batch cannot look complete.
 */
export async function runLocalPreparation({ target, cases, sessionCookie, send }) {
  if (!Array.isArray(cases) || cases.length < 1 || cases.length > 10) throw Error('local_case_limit');
  // Validate the whole batch before any request, including cases after the first.
  for (const item of cases) comparisonPath(item);
  const outcomes = [];
  for (const item of cases) {
    try {
      const response = await sendLocalCase({ target, item, sessionCookie, send });
      if (!response || !Number.isInteger(response.status) || response.status < 100 || response.status > 599) throw Error('invalid_status');
      outcomes.push({ kind: item.kind, status: response.status, correctness: 'unchecked' });
    } catch (_) {
      return { completed: false, outcomes, failure: 'transport_or_input_error', measurement: false };
    }
  }
  return { completed: true, outcomes, measurement: false };
}
