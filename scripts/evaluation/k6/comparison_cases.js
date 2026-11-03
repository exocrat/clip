/** Permit only the loopback API root or the integrated website's /api mount. */
export function localApiTarget(target) {
  if (typeof target !== 'string' || !/^http:\/\/127\.0\.0\.1:[1-9][0-9]{0,4}(?:\/api)?$/.test(target)) throw Error('local_target_required');
  const port = Number(target.slice('http://127.0.0.1:'.length).split('/')[0]);
  if (port > 65535) throw Error('local_target_required');
  return target;
}

/** Accept a deployed API root only when it is bound to the planned HTTPS origin. */
export function approvedApiTarget(target, origin) {
  let parsedOrigin;
  try { parsedOrigin = new URL(origin); } catch (_) { throw Error('approved_https_target_required'); }
  if (parsedOrigin.protocol !== 'https:' || parsedOrigin.username || parsedOrigin.password || parsedOrigin.pathname !== '/' || parsedOrigin.search || parsedOrigin.hash || !parsedOrigin.hostname || target !== `${parsedOrigin.origin}/api`) throw Error('approved_https_target_required');
  return target;
}

/** Build one contract-shaped read path from a reviewed comparison case.
 * The caller supplies an authenticated session separately; this function never
 * handles credentials or sends requests. Cases are inputs, not result oracles.
 */
export function comparisonPath(item) {
  if (!item || typeof item !== 'object' || Array.isArray(item)) throw Error('invalid_case');
  if (item.kind === 'detail') {
    if (Object.keys(item).some(k => !['kind', 'listing_id'].includes(k)) ||
        typeof item.listing_id !== 'string' ||
        !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(item.listing_id)) throw Error('invalid_detail');
    return `/listings/${item.listing_id}`;
  }
  if (!['browse', 'search'].includes(item.kind) || Object.keys(item).some(k => !['kind', 'query'].includes(k))) throw Error('invalid_case');
  const query = item.query;
  if (!query || typeof query !== 'object' || Array.isArray(query)) throw Error('invalid_query');
  const allowed = ['q', 'search_mode', 'sort', 'page', 'page_size', 'category_code', 'condition_code', 'negotiable', 'min_price_paise', 'max_price_paise'];
  if (Object.keys(query).some(k => !allowed.includes(k))) throw Error('invalid_query');
  // The generated API defaults to keyword; Hybrid must be explicit for parity.
  if (item.kind === 'search' && (typeof query.q !== 'string' || !query.q.trim() || query.search_mode !== 'hybrid')) throw Error('invalid_search');
  if (item.kind === 'browse' && (query.q !== undefined || query.search_mode !== undefined)) throw Error('invalid_browse');
  const parts = [];
  for (const key of allowed) {
    if (query[key] === undefined) continue;
    const values = Array.isArray(query[key]) ? query[key] : [query[key]];
    if (!values.length || values.some(v => !['string', 'number', 'boolean'].includes(typeof v) || String(v).length === 0 || typeof v === 'number' && !Number.isSafeInteger(v))) throw Error('invalid_query');
    if (Array.isArray(query[key]) && !['category_code', 'condition_code'].includes(key)) throw Error('invalid_query');
    for (const value of values) parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
  }
  return `/listings${parts.length ? `?${parts.join('&')}` : ''}`;
}
