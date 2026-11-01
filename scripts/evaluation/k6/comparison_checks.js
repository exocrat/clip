/** Contract-shaped correctness checks against independently prepared cases.
 * Expected data must be reviewed separately; this module never derives an oracle
 * from the response under test and never records response content.
 */
import { SUMMARY_FIELDS } from './core.js';

const uuid = value => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
const exactKeys = (value, keys) => value !== null && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value,key));
const same = (a,b) => {
  if (a === b) return true;
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((v,i) => same(v,b[i]));
  if (!a || !b || typeof a !== 'object' || typeof b !== 'object' || Array.isArray(a) || Array.isArray(b)) return false;
  const keys=Object.keys(a); return keys.length === Object.keys(b).length && keys.every(k => Object.hasOwn(b,k) && same(a[k],b[k]));
};

function validListing(row, detail, query) {
  if (!exactKeys(row, detail ? [...SUMMARY_FIELDS,'proof_available'] : SUMMARY_FIELDS) || !uuid(row.listing_id)) return false;
  if (typeof row.title !== 'string' || !row.title.trim() || typeof row.description !== 'string') return false;
  if (!['category_code','category_label','condition_code','condition_label'].every(k => typeof row[k] === 'string' && row[k])) return false;
  if (!Number.isSafeInteger(row.asking_price_paise) || row.asking_price_paise < 0 || row.asking_price_paise > 1_000_000_000 || row.asking_price_paise % 100 !== 0) return false;
  if (!(row.original_price_paise === null || Number.isSafeInteger(row.original_price_paise) && row.original_price_paise > 0 && row.original_price_paise <= 1_000_000_000 && row.original_price_paise % 100 === 0)) return false;
  if (typeof row.negotiable !== 'boolean' || typeof row.sensitive_purchase !== 'boolean' || !(row.pickup_area === null || typeof row.pickup_area === 'string')) return false;
  if (row.availability !== 'available' || typeof row.available_from !== 'string' || !Number.isFinite(Date.parse(row.available_from)) || !(row.available_until === null || typeof row.available_until === 'string' && Number.isFinite(Date.parse(row.available_until)))) return false;
  if (Date.parse(row.available_from) > Date.now() || row.available_until !== null && Date.parse(row.available_until) <= Date.now()) return false;
  if (!Array.isArray(row.image_ids) || !row.image_ids.every(uuid) || (detail && !(row.proof_available === null || typeof row.proof_available === 'boolean'))) return false;
  for (const key of ['category_code','condition_code']) if (query[key] !== undefined && !(Array.isArray(query[key]) ? query[key] : [query[key]]).includes(row[key])) return false;
  if (query.negotiable !== undefined && row.negotiable !== query.negotiable || query.min_price_paise !== undefined && row.asking_price_paise < query.min_price_paise || query.max_price_paise !== undefined && row.asking_price_paise > query.max_price_paise) return false;
  return true;
}

/** Require the expected shape and exact ordered page/detail, including fields. */
export function validExpected(request, expected) {
  if (request.kind === 'detail') return validListing(expected,true,{}) && expected.listing_id === request.listing_id;
  if (!['browse','search'].includes(request.kind) || !exactKeys(expected,['items','page','page_size','has_next']) || !Array.isArray(expected.items)) return false;
  const q=request.query;
  if (expected.page !== (q.page ?? 1) || expected.page_size !== (q.page_size ?? 20) || typeof expected.has_next !== 'boolean' || expected.items.length > expected.page_size || (expected.has_next && expected.items.length !== expected.page_size)) return false;
  const ids=expected.items.map(row => row?.listing_id);
  return new Set(ids).size === ids.length && expected.items.every(row => validListing(row,false,q));
}

/** A non-200, malformed or mismatched response is never a correct completion. */
export function correctResponse(status, actual, request, expected) {
  return status === 200 && validExpected(request,expected) && validExpected(request,actual) && same(actual,expected);
}
