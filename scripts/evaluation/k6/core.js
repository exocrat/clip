/** Pure workload/response checks shared by k6 and Node tests; no network or globals. */
export const SUMMARY_FIELDS = ['listing_id','title','description','category_code','category_label','condition_code','condition_label','asking_price_paise','original_price_paise','negotiable','pickup_area','available_from','available_until','availability','sensitive_purchase','image_ids'];
const uuid = value => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(value);
const exactKeys = (value, keys) => value !== null && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value,key));
const instant = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$/.test(value) && Number.isFinite(Date.parse(value));

/** Reject draft/cloud execution, actor selectors, unsafe URLs and unbounded local load. */
export function validateProfile(p) {
  if (!exactKeys(p,['version','id','purpose','rate','warmup_seconds','measured_seconds','max_vus','timeout_seconds','cases'])) throw Error('invalid_profile');
  if (p.version !== 1 || !/^[a-z0-9-]+$/.test(p.id) || !['local-pilot','nfr-draft'].includes(p.purpose)) throw Error('invalid_profile');
  for (const key of ['rate','warmup_seconds','measured_seconds','max_vus']) if (!Number.isInteger(p[key])) throw Error('invalid_profile');
  if (p.rate < 1 || p.warmup_seconds < 0 || p.measured_seconds < 1 || p.max_vus < 1 || !(p.timeout_seconds > 0)) throw Error('invalid_profile');
  if (p.purpose === 'local-pilot' && (p.rate > 2 || p.warmup_seconds > 5 || p.measured_seconds > 10 || p.max_vus > 2 || p.timeout_seconds > 3)) throw Error('pilot_cap_exceeded');
  if (!Array.isArray(p.cases) || !p.cases.length || p.cases.length > 20) throw Error('invalid_cases');
  const ids = new Set();
  for (const item of p.cases) {
    if (!exactKeys(item,['id','query','expected_ids']) || !/^[a-z0-9-]+$/.test(item.id) || ids.has(item.id)) throw Error('invalid_case');
    ids.add(item.id);
    const q = item.query;
    if (q === null || typeof q !== 'object' || Array.isArray(q) || Object.keys(q).some(key => !['q','search_mode','sort','page','page_size','category_code','condition_code','negotiable','min_price_paise','max_price_paise'].includes(key))) throw Error('invalid_query');
    if (q.q !== undefined && (typeof q.q !== 'string' || [...q.q.trim()].length > 120)) throw Error('invalid_query');
    if (q.search_mode !== undefined && !['keyword','hybrid'].includes(q.search_mode)) throw Error('invalid_query');
    if (q.sort !== undefined && !['created_desc','price_asc','price_desc','relevance'].includes(q.sort)) throw Error('invalid_query');
    if (q.sort === 'relevance' && !q.q?.trim()) throw Error('invalid_query');
    if (q.page !== undefined && (!Number.isSafeInteger(q.page) || q.page < 1)) throw Error('invalid_query');
    if (q.page_size !== undefined && ![20,50,100].includes(q.page_size)) throw Error('invalid_query');
    for (const key of ['category_code','condition_code']) if (q[key] !== undefined && typeof q[key] !== 'string') throw Error('invalid_query');
    if (q.negotiable !== undefined && typeof q.negotiable !== 'boolean') throw Error('invalid_query');
    for (const key of ['min_price_paise','max_price_paise']) if (q[key] !== undefined && (!Number.isSafeInteger(q[key]) || q[key] < 0 || q[key] % 100 !== 0)) throw Error('invalid_query');
    if (q.min_price_paise !== undefined && q.max_price_paise !== undefined && q.min_price_paise > q.max_price_paise) throw Error('invalid_query');
    if (p.purpose === 'local-pilot' && (!Array.isArray(item.expected_ids) || !item.expected_ids.length || !item.expected_ids.every(uuid))) throw Error('fixture_oracle_required');
    if (p.purpose === 'nfr-draft' && item.expected_ids !== null) throw Error('draft_oracle_must_be_unresolved');
  }
  return p;
}

/** Exact public page shape plus fixture oracle membership, coordinates and freshness. */
export function validPage(value, item) {
  if (!exactKeys(value,['items','page','page_size','has_next']) || !Array.isArray(value.items) || value.page !== (item.query.page ?? 1) || value.page_size !== (item.query.page_size ?? 20) || typeof value.has_next !== 'boolean' || value.items.length > value.page_size || (value.has_next && value.items.length !== value.page_size)) return false;
  const seen = new Set();
  for (const row of value.items) {
    if (!exactKeys(row,SUMMARY_FIELDS) || !uuid(row.listing_id) || seen.has(row.listing_id)) return false;
    seen.add(row.listing_id);
    if (typeof row.title !== 'string' || !row.title.trim() || [...row.title].length > 120 || typeof row.description !== 'string' || [...row.description].length > 5000) return false;
    if (!['category_code','category_label','condition_code','condition_label'].every(key => typeof row[key] === 'string' && row[key])) return false;
    if (!Number.isSafeInteger(row.asking_price_paise) || row.asking_price_paise < 0 || row.asking_price_paise % 100 !== 0 || typeof row.negotiable !== 'boolean' || typeof row.sensitive_purchase !== 'boolean' || row.availability !== 'available') return false;
    if (!(row.original_price_paise === null || Number.isSafeInteger(row.original_price_paise) && row.original_price_paise > 0 && row.original_price_paise <= 1_000_000_000 && row.original_price_paise % 100 === 0)) return false;
    if (!(row.pickup_area === null || typeof row.pickup_area === 'string') || !instant(row.available_from) || !(row.available_until === null || instant(row.available_until)) || !Array.isArray(row.image_ids) || !row.image_ids.every(uuid)) return false;
    if (Date.parse(row.available_from) > Date.now() || row.available_until !== null && Date.parse(row.available_until) <= Date.now()) return false;
    const q = item.query;
    if (q.category_code !== undefined && q.category_code !== row.category_code || q.condition_code !== undefined && q.condition_code !== row.condition_code || q.negotiable !== undefined && q.negotiable !== row.negotiable || q.min_price_paise !== undefined && row.asking_price_paise < q.min_price_paise || q.max_price_paise !== undefined && row.asking_price_paise > q.max_price_paise) return false;
  }
  return item.expected_ids.every(id => seen.has(id));
}

/** Two arrival cohorts with bounded drain between them prevent warm/measured overlap. */
export function scenarios(p) {
  const timeout = `${p.timeout_seconds}s`;
  const scenario = (duration, startTime) => ({executor:'constant-arrival-rate',rate:p.rate,timeUnit:'1s',duration:`${duration}s`,startTime:`${startTime}s`,preAllocatedVUs:p.max_vus,maxVUs:p.max_vus,gracefulStop:timeout});
  return { ...(p.warmup_seconds ? { warmup:scenario(p.warmup_seconds,0) } : {}), measured:scenario(p.measured_seconds,p.warmup_seconds ? p.warmup_seconds + p.timeout_seconds : 0) };
}
