// Offline parity check: callers supply already collected, synthetic-safe inputs.
// This function makes no requests and does not establish deployment identity.
import { equivalentSearchResponses } from './comparison_checks.js';

/** Compare three distinct search cases without returning the response contents. */
export function checkSearchParity(cases) {
  if (!Array.isArray(cases) || cases.length !== 3) throw Error('three_search_cases_required');
  const seen = new Set();
  let matched = 0;
  for (const item of cases) {
    if (!item || typeof item !== 'object' || Array.isArray(item) ||
        Object.keys(item).sort().join(',') !== 'a,b,request' ||
        item.request?.kind !== 'search' || typeof item.request.query?.q !== 'string' ||
        !item.request.query.q.trim() || seen.has(item.request.query.q) ||
        ![item.a, item.b].every(value => value && typeof value === 'object' &&
          !Array.isArray(value) && Object.keys(value).sort().join(',') === 'body,status' &&
          Number.isInteger(value.status))) throw Error('invalid_search_case');
    seen.add(item.request.query.q);
    if (equivalentSearchResponses(item.a.status, item.a.body, item.b.status, item.b.body, item.request)) matched += 1;
  }
  return { cases_checked: 3, cases_equal_and_valid: matched, all_equal_and_valid: matched === 3,
    independent_correctness_verified: false, deployment_verified: false, measurement_authorized: false };
}
