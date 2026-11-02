// Offline comparison only: no requests, credentials or deployment checks.
import { equivalentReadResponses } from './comparison_checks.js';
import { canonical, checkSearchParity } from './comparison_search_parity.js';

/** Compare the complete 5 browse / 3 search / 2 detail corpus without returning bodies. */
export function checkAllParity(cases, corpus) {
  if (!Array.isArray(cases) || cases.length !== 10 || !Array.isArray(corpus?.cases) || corpus.cases.length !== 10) throw Error('ten_cases_required');
  const expected = new Map();
  const counts = {browse:0,search:0,detail:0};
  for (const item of corpus.cases) {
    const kind=item?.request?.kind;
    if (!Object.hasOwn(counts,kind) || typeof item.case_id !== 'string' || !item.case_id || expected.has(item.case_id)) throw Error('invalid_corpus');
    expected.set(item.case_id,item); counts[kind]++;
  }
  if (counts.browse !== 5 || counts.search !== 3 || counts.detail !== 2) throw Error('invalid_case_mix');
  const seen=new Set(); const searches=[]; let matched=0;
  for (const item of cases) {
    const target=expected.get(item?.case_id);
    if (!item || typeof item !== 'object' || Array.isArray(item) || Object.keys(item).sort().join(',') !== 'a,b,case_id,request' ||
        !target || seen.has(item.case_id) || JSON.stringify(canonical(item.request)) !== JSON.stringify(canonical(target.request)) ||
        ![item.a,item.b].every(side => side && typeof side === 'object' && !Array.isArray(side) && Object.keys(side).sort().join(',') === 'body,status' && Number.isInteger(side.status))) throw Error('invalid_case');
    seen.add(item.case_id);
    if (item.request.kind === 'search') searches.push(item);
    else if (equivalentReadResponses(item.a.status,item.a.body,item.b.status,item.b.body,item.request)) matched++;
  }
  matched += checkSearchParity(searches,corpus).cases_equal_and_valid;
  return {cases_checked:10,cases_equal_and_valid:matched,all_equal_and_valid:matched === 10,
    corpus_authenticity_verified:false,independent_correctness_verified:false,deployment_verified:false,measurement_authorized:false};
}
