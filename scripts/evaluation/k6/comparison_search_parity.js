// Offline parity check: callers supply already collected, synthetic-safe inputs.
// This function makes no requests and does not establish deployment identity.
import { equivalentSearchResponses } from './comparison_checks.js';

export const canonical = value => {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  return value;
};

/** Compare the three search cases in the supplied corpus without returning contents. */
export function checkSearchParity(cases, corpus) {
  if (!Array.isArray(cases) || cases.length !== 3) throw Error('three_search_cases_required');
  if (!corpus || !Array.isArray(corpus.cases)) throw Error('search_corpus_required');
  const expected = corpus.cases.filter(item => item?.request?.kind === 'search');
  const classes = expected.map(item => item.relevance_reference?.query_class).sort();
  if (expected.length !== 3 || classes.join(',') !== 'direct_word,meaning_based,related_word' ||
      new Set(expected.map(item => item.case_id)).size !== 3 ||
      expected.some(item => typeof item.case_id !== 'string' || !item.case_id)) throw Error('invalid_search_corpus');
  const byId = new Map(expected.map(item => [item.case_id, item]));
  const seen = new Set();
  let matched = 0;
  for (const item of cases) {
    if (!item || typeof item !== 'object' || Array.isArray(item) ||
        Object.keys(item).sort().join(',') !== 'a,b,case_id,request' ||
        !byId.has(item.case_id) || seen.has(item.case_id) ||
        item.request?.kind !== 'search' || typeof item.request.query?.q !== 'string' ||
        !item.request.query.q.trim() ||
        JSON.stringify(canonical(item.request)) !== JSON.stringify(canonical(byId.get(item.case_id).request)) ||
        ![item.a, item.b].every(value => value && typeof value === 'object' &&
          !Array.isArray(value) && Object.keys(value).sort().join(',') === 'body,status' &&
          Number.isInteger(value.status))) throw Error('invalid_search_case');
    seen.add(item.case_id);
    if (equivalentSearchResponses(item.a.status, item.a.body, item.b.status, item.b.body, item.request)) matched += 1;
  }
  return { cases_checked: 3, cases_equal_and_valid: matched, all_equal_and_valid: matched === 3,
    corpus_authenticity_verified: false, independent_correctness_verified: false,
    deployment_verified: false, measurement_authorized: false };
}
