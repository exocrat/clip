import { MAX_MARKETPLACE_PRICE_PAISE } from '../../shared/money';

/** Reviewed query values; money stays decimal text to avoid JavaScript rounding. */
export type DiscoveryQuery = {
  q: string; category_code: string[]; condition_code: string[];
  min_price_paise: string; max_price_paise: string;
  sort: 'created_desc' | 'price_asc' | 'price_desc' | 'relevance'; sort_explicit: boolean;
  search_mode: 'keyword' | 'hybrid';
  page: number; page_size: 20 | 50 | 100;
};

export type DiscoveryForm = Omit<DiscoveryQuery, 'min_price_paise' | 'max_price_paise' | 'page' | 'search_mode'> & {
  min_rupees: string; max_rupees: string;
};

/** User-facing default; explicit Keyword links remain supported for compatibility. */
export const DEFAULT_QUERY: DiscoveryQuery = {
  q: '', category_code: [], condition_code: [], min_price_paise: '', max_price_paise: '',
  search_mode: 'hybrid', sort: 'created_desc', sort_explicit: false, page: 1, page_size: 20,
};

/** Safe validation messages contain field names only, never raw URL/provider data. */
export class DiscoveryQueryError extends Error {}

/** Parse exact nonnegative decimal integers without a floating-point conversion. */
function integerText(value: string): string {
  if (!/^[0-9]+$/.test(value)) throw new DiscoveryQueryError('Prices must be whole rupees.');
  return BigInt(value).toString();
}

/** Validate search URLs; repeated catalogue values are multi-choice, and legacy negotiability is ignored. */
export function parseDiscoveryQuery(params: URLSearchParams): DiscoveryQuery {
  const keys = new Set(['q', 'category_code', 'condition_code', 'min_price_paise', 'max_price_paise',
    'negotiable', 'sort', 'search_mode', 'page', 'page_size']);
  const multiChoiceKeys = new Set(['category_code', 'condition_code']);
  for (const key of params.keys()) {
    if (!keys.has(key) || (!multiChoiceKeys.has(key) && params.getAll(key).length !== 1)) {
      throw new DiscoveryQueryError('The URL has invalid filters. Apply your filters again or reset them.');
    }
  }
  const q = (params.get('q') ?? '').trim();
  if ([...q].length > 120) throw new DiscoveryQueryError('Search text must be 120 characters or fewer.');
  const prices = ['min_price_paise', 'max_price_paise'].map((key) => {
    const value = params.get(key);
    if (value === null) return '';
    const result = integerText(value);
    if (BigInt(result) % 100n !== 0n) throw new DiscoveryQueryError('Prices must be whole rupees.');
    if (BigInt(result) > BigInt(MAX_MARKETPLACE_PRICE_PAISE)) throw new DiscoveryQueryError('Prices must be ₹1,00,00,000 or less.');
    return result;
  });
  if (prices[0] && prices[1] && BigInt(prices[0]) > BigInt(prices[1])) throw new DiscoveryQueryError('Minimum price must not exceed maximum price.');
  const rawPage = params.get('page') ?? '1';
  const rawSize = params.get('page_size') ?? '20';
  if (!/^[0-9]+$/.test(rawPage) || !Number.isSafeInteger(Number(rawPage)) || Number(rawPage) < 1) throw new DiscoveryQueryError('The page number cannot be displayed safely. Reset to page 1.');
  if (!['20', '50', '100'].includes(rawSize)) throw new DiscoveryQueryError('Choose 20, 50 or 100 listings per page.');
  const search_mode = params.get('search_mode') ?? 'hybrid';
  if (!['keyword', 'hybrid'].includes(search_mode)) throw new DiscoveryQueryError('The search settings in this link are invalid.');
  const sort = params.get('sort') ?? (q ? 'relevance' : 'created_desc');
  const legacyNegotiable = params.get('negotiable');
  if (!['created_desc', 'price_asc', 'price_desc', 'relevance'].includes(sort) ||
    (legacyNegotiable !== null && !['', 'true', 'false'].includes(legacyNegotiable))) {
    throw new DiscoveryQueryError('The sort or search settings are invalid.');
  }
  if (sort === 'relevance' && !q) throw new DiscoveryQueryError('Enter search text to sort by relevance.');
  const selections = (key: string) => [...new Set(params.getAll(key))].sort();
  return { q, search_mode: search_mode as DiscoveryQuery['search_mode'], category_code: selections('category_code'), condition_code: selections('condition_code'),
    min_price_paise: prices[0], max_price_paise: prices[1],
    sort: sort as DiscoveryQuery['sort'], sort_explicit: params.has('sort'),
    page: Number(rawPage), page_size: Number(rawSize) as DiscoveryQuery['page_size'] };
}

/** Serialize only reviewed fields, preserving explicit zero/false and stable defaults. */
export function discoveryParams(query: DiscoveryQuery): URLSearchParams {
  const params = new URLSearchParams();
  for (const key of ['q', 'min_price_paise', 'max_price_paise'] as const) {
    if (query[key] !== '') params.set(key, query[key]);
  }
  for (const key of ['category_code', 'condition_code'] as const) {
    for (const value of [...new Set(query[key])].sort()) params.append(key, value);
  }
  if (query.search_mode !== 'hybrid') params.set('search_mode', query.search_mode);
  const defaultSort = query.q ? 'relevance' : 'created_desc';
  if (query.sort !== defaultSort || query.sort_explicit) params.set('sort', query.sort);
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

/** A changed search term starts with automatic matching, while filters keep its chosen sort. */
export function editDiscoveryText(form: DiscoveryForm, q: string): DiscoveryForm {
  return { ...form, q, sort: q.trim() ? 'relevance' : 'created_desc', sort_explicit: false };
}

/** Apply draft controls atomically; any filter/sort/page-size submission resets page 1. */
export function applyDiscoveryForm(form: DiscoveryForm, mode: DiscoveryQuery['search_mode'] = 'hybrid'): DiscoveryQuery {
  const { min_rupees, max_rupees, ...rest } = form;
  const q = rest.q.trim();
  const query = { ...rest, q, search_mode: mode, page: 1,
    sort: q ? (rest.sort_explicit ? rest.sort : 'relevance' as const)
      : rest.sort === 'relevance' ? 'created_desc' as const : rest.sort,
    min_price_paise: min_rupees.trim() ? (BigInt(integerText(min_rupees.trim())) * 100n).toString() : '',
    max_price_paise: max_rupees.trim() ? (BigInt(integerText(max_rupees.trim())) * 100n).toString() : '' };
  return parseDiscoveryQuery(discoveryParams(query));
}


/** Mode changes act on applied inputs only; callers preserve the separate form draft. */
export function switchDiscoveryMode(query: DiscoveryQuery, mode: DiscoveryQuery['search_mode']): DiscoveryQuery {
  return { ...query, search_mode: mode, page: 1 };
}
