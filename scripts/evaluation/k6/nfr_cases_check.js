/** Offline shape and expected-response checks. This is never run authorization. */
import { comparisonPath } from './comparison_cases.js';
import { validExpected } from './comparison_checks.js';

/** Validate one selected NFR's cases; no review or dataset binding is attested. */
export function validateNfrCases(bundle, nfr) {
  if (!bundle || bundle.format_version !== 1 || bundle.purpose !== 'nfr-case-drafts-not-executable' || bundle.execution_permitted !== false || bundle.nfr_accepted !== false) throw Error('invalid_draft_bundle');
  if (!['nfr-01', 'nfr-02'].includes(nfr)) throw Error('invalid_nfr');
  const browse = nfr === 'nfr-01';
  const cases = bundle[browse ? 'nfr_01' : 'nfr_02'];
  if (!Array.isArray(cases) || cases.length !== (browse ? 5 : 3)) throw Error('invalid_case_count');
  const ids = new Set();
  for (const item of cases) {
    if (!item || typeof item.case_id !== 'string' || !item.case_id || ids.has(item.case_id) || item.expected_status !== 200 || item.request?.kind !== (browse ? 'browse' : 'search')) throw Error('invalid_case');
    ids.add(item.case_id);
    comparisonPath(item.request);
    if (!validExpected(item.request, item.expected)) throw Error('missing_or_invalid_expected');
  }
  if (browse) {
    if (!cases.some(c => (c.request.query.page ?? 1) === 1) || !cases.some(c => c.request.query.page > 1) || !cases.some(c => c.request.query.category_code !== undefined)) throw Error('missing_browse_coverage');
  } else {
    const classes = cases.map(c => c.relevance_reference?.query_class).sort();
    if (classes.join(',') !== 'direct_word,meaning_based,related_word') throw Error('missing_query_classes');
  }
  return { nfr, case_shapes_valid: true, execution_permitted: false, nfr_accepted: false,
    limitations: ['dataset and source binding not independently verified', 'reference review not attested', 'actual deployed responses not checked'] };
}
