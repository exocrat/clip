/** Reviewed query values; money stays decimal text to avoid JavaScript rounding. */
export type DiscoveryQuery = {
  q: string; category_code: string; condition_code: string;
  min_price_paise: string; max_price_paise: string;
  negotiable: '' | 'true' | 'false'; sort: 'created_desc' | 'price_asc' | 'price_desc' | 'relevance';
  search_mode: 'keyword' | 'hybrid';
  page: number; page_size: 20 | 50 | 100;
};

export type DiscoveryForm = Omit<DiscoveryQuery, 'min_price_paise' | 'max_price_paise' | 'page' | 'search_mode'> & {
  min_rupees: string; max_rupees: string;
};

export const DEFAULT_QUERY: DiscoveryQuery = {
  q: '', category_code: '', condition_code: '', min_price_paise: '', max_price_paise: '',
  negotiable: '', search_mode: 'keyword', sort: 'created_desc', page: 1, page_size: 20,
};

/** Safe validation messages contain field names only, never raw URL/provider data. */
export class DiscoveryQueryError extends Error {}

/** Parse exact nonnegative decimal integers without a floating-point conversion. */
function integerText(value: string): string {
  if (!/^[0-9]+$/.test(value)) throw new DiscoveryQueryError('Prices must be whole rupees.');
  return BigInt(value).toString();
}

/** Validate the approved URL shape; duplicate/unknown fields cannot select an actor. */
export function parseDiscoveryQuery(params: URLSearchParams): DiscoveryQuery {
  const keys = new Set(Object.keys(DEFAULT_QUERY));
  for (const key of params.keys()) {
    if (!keys.has(key) || params.getAll(key).length !== 1) throw new DiscoveryQueryError('The URL has invalid filters. Apply your filters again or reset them.');
  }
  const q = (params.get('q') ?? '').trim();
  if ([...q].length > 120) throw new DiscoveryQueryError('Search text must be 120 characters or fewer.');
  const prices = ['min_price_paise', 'max_price_paise'].map((key) => {
    const value = params.get(key);
    if (value === null) return '';
    const result = integerText(value);
    if (BigInt(result) % 100n !== 0n) throw new DiscoveryQueryError('Prices must be whole rupees.');
    return result;
  });
  if (prices[0] && prices[1] && BigInt(prices[0]) > BigInt(prices[1])) throw new DiscoveryQueryError('Minimum price must not exceed maximum price.');
  const rawPage = params.get('page') ?? '1';
  const rawSize = params.get('page_size') ?? '20';
  if (!/^[0-9]+$/.test(rawPage) || !Number.isSafeInteger(Number(rawPage)) || Number(rawPage) < 1) throw new DiscoveryQueryError('The page number cannot be displayed safely. Reset to page 1.');
  if (!['20', '50', '100'].includes(rawSize)) throw new DiscoveryQueryError('Choose 20, 50 or 100 listings per page.');
  const search_mode = params.get('search_mode') ?? 'keyword';
  if (!['keyword', 'hybrid'].includes(search_mode)) throw new DiscoveryQueryError('Choose Keyword or Hybrid search.');
  const sort = params.get('sort') ?? 'created_desc';
  const negotiable = params.get('negotiable') ?? '';
  if (!['created_desc', 'price_asc', 'price_desc', 'relevance'].includes(sort) || !['', 'true', 'false'].includes(negotiable)) throw new DiscoveryQueryError('The sort or negotiability filter is invalid.');
  if (sort === 'relevance' && !q) throw new DiscoveryQueryError('Enter search text to sort by relevance.');
  return { q, search_mode: search_mode as DiscoveryQuery['search_mode'], category_code: params.get('category_code') ?? '', condition_code: params.get('condition_code') ?? '',
    min_price_paise: prices[0], max_price_paise: prices[1],
    negotiable: negotiable as DiscoveryQuery['negotiable'], sort: sort as DiscoveryQuery['sort'],
    page: Number(rawPage), page_size: Number(rawSize) as DiscoveryQuery['page_size'] };
}

/** Serialize only reviewed fields, preserving explicit zero/false and stable defaults. */
export function discoveryParams(query: DiscoveryQuery): URLSearchParams {
  const params = new URLSearchParams();
  for (const key of ['q', 'category_code', 'condition_code', 'min_price_paise', 'max_price_paise', 'negotiable'] as const) {
    if (query[key] !== '') params.set(key, query[key]);
  }
  if (query.search_mode !== 'keyword') params.set('search_mode', query.search_mode);
  if (query.sort !== 'created_desc') params.set('sort', query.sort);
  if (query.page > 1) params.set('page', String(query.page));
  if (query.page_size !== 20) params.set('page_size', String(query.page_size));
  return params;
}

/** Convert paise text for display/editing without changing an unstated price to zero. */
export function discoveryForm(query: DiscoveryQuery): DiscoveryForm {
  const { min_price_paise, max_price_paise, page: _page, search_mode: _mode, ...rest } = query;
  return { ...rest, min_rupees: min_price_paise ? (BigInt(min_price_paise) / 100n).toString() : '',
    max_rupees: max_price_paise ? (BigInt(max_price_paise) / 100n).toString() : '' };
}

/** Apply draft controls atomically; any filter/sort/page-size submission resets page 1. */
export function applyDiscoveryForm(form: DiscoveryForm, mode: DiscoveryQuery['search_mode'] = 'keyword'): DiscoveryQuery {
  const { min_rupees, max_rupees, ...rest } = form;
  const query = { ...rest, search_mode: mode, page: 1,
    sort: !rest.q.trim() && rest.sort === 'relevance' ? 'created_desc' as const : rest.sort,
    min_price_paise: min_rupees.trim() ? (BigInt(integerText(min_rupees.trim())) * 100n).toString() : '',
    max_price_paise: max_rupees.trim() ? (BigInt(integerText(max_rupees.trim())) * 100n).toString() : '' };
  return parseDiscoveryQuery(discoveryParams(query));
}


/** Mode changes act on applied inputs only; callers preserve the separate form draft. */
export function switchDiscoveryMode(query: DiscoveryQuery, mode: DiscoveryQuery['search_mode']): DiscoveryQuery {
  return { ...query, search_mode: mode, page: 1 };
}
