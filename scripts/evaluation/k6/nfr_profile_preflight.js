/** Offline draft-shape preflight; it does not authorize sessions or execution. */
import { comparisonPath } from './comparison_cases.js';
import { validateProfile } from './core.js';

const keys = ['version', 'id', 'purpose', 'rate', 'warmup_seconds', 'measured_seconds', 'max_vus', 'timeout_seconds', 'cases'];
const caseKeys = ['id', 'query', 'expected_ids'];
const exact = (v, names) => v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === names.length && names.every(k => Object.hasOwn(v, k));
const uuid = v => typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v);

/** Validate NFR-01 response IDs or NFR-02 query inputs without claiming review. */
export function validateNfrDraft(profile, nfr) {
  if (!['nfr-01', 'nfr-02'].includes(nfr)) throw Error('invalid_nfr');
  if (!exact(profile, keys) || profile.version !== 1 || profile.purpose !== 'nfr-draft' || typeof profile.id !== 'string' || !/^[a-z0-9-]{1,80}$/.test(profile.id)) throw Error('invalid_profile');
  const rate = nfr === 'nfr-01' ? 20 : 10;
  if (profile.rate !== rate || profile.warmup_seconds !== 60 || profile.measured_seconds !== 300 || profile.timeout_seconds !== 5) throw Error('design_values_mismatch');
  if (!Number.isSafeInteger(profile.max_vus) || profile.max_vus < 1) throw Error('invalid_capacity');
  if (!Array.isArray(profile.cases) || profile.cases.length < 1 || profile.cases.length > 20) throw Error('invalid_cases');
  // Reuse the existing draft query validator; the supplied IDs are checked below.
  validateProfile({...profile, cases: profile.cases.map(item => ({...item, expected_ids: null}))});
  const ids = new Set();
  for (const item of profile.cases) {
    if (!exact(item, caseKeys) || typeof item.id !== 'string' || !/^[a-z0-9-]{1,80}$/.test(item.id) || ids.has(item.id)) throw Error('invalid_case');
    ids.add(item.id);
    comparisonPath({kind: nfr === 'nfr-01' ? 'browse' : 'search', query: item.query});
    if (nfr === 'nfr-01') {
      if (!Array.isArray(item.expected_ids) || item.expected_ids.length > (item.query.page_size ?? 20) || !item.expected_ids.every(uuid) || new Set(item.expected_ids).size !== item.expected_ids.length) throw Error('expected_ids_required');
    } else if (item.expected_ids !== null) {
      throw Error('search_ranking_not_part_of_latency_nfr');
    }
  }
  return { nfr, draft_shape_valid: true, execution_permitted: false, nfr_accepted: false,
    limitations: ['not a reviewed oracle', 'dataset and source bindings unverified', 'NFR-02 does not score search relevance; NFR-04 owns Success@5', 'case coverage and full response assertions unverified', 'capacity, retries, clock, session and target unverified'] };
}
