import { MAX_MARKETPLACE_PRICE_PAISE } from '../../shared/money';

/** URL and form state for public Wanted Request discovery. */
export type WantedDiscoveryQuery = {
  q: string;
  category_code: string[];
  min_budget_paise: string;
  max_budget_paise: string;
  page: number;
  page_size: 20 | 50 | 100;
};

export type WantedDiscoveryForm = Omit<
  WantedDiscoveryQuery,
  'min_budget_paise' | 'max_budget_paise' | 'page'
> & { min_rupees: string; max_rupees: string };

export const DEFAULT_WANTED_QUERY: WantedDiscoveryQuery = {
  q: '', category_code: [], min_budget_paise: '', max_budget_paise: '', page: 1, page_size: 20,
};

/** Safe messages avoid reflecting malformed or untrusted URL values. */
export class WantedDiscoveryQueryError extends Error {}

function integerText(value: string): string {
  if (!/^[0-9]+$/.test(value)) throw new WantedDiscoveryQueryError('Budgets must be whole rupees.');
  return BigInt(value).toString();
}

/** Parse URL state, accepting category values as repeated query parameters. */
export function parseWantedDiscoveryQuery(params: URLSearchParams): WantedDiscoveryQuery {
  const multiChoice = new Set(['category_code']);
  const accepted = new Set(['q', 'category_code', 'min_budget_paise', 'max_budget_paise', 'page', 'page_size']);
  for (const key of params.keys()) {
    if (!accepted.has(key) || (!multiChoice.has(key) && params.getAll(key).length !== 1)) {
      throw new WantedDiscoveryQueryError('This Wanted Request link has invalid filters. Reset the filters and try again.');
    }
  }
  const q = (params.get('q') ?? '').trim();
  if ([...q].length > 120) throw new WantedDiscoveryQueryError('Search text must be 120 characters or fewer.');
  const budgets = (['min_budget_paise', 'max_budget_paise'] as const).map((key) => {
    const value = params.get(key);
    if (value === null) return '';
    const exact = integerText(value);
    if (BigInt(exact) % 100n !== 0n) throw new WantedDiscoveryQueryError('Budgets must be whole rupees.');
    if (BigInt(exact) > BigInt(MAX_MARKETPLACE_PRICE_PAISE)) throw new WantedDiscoveryQueryError('Budgets must be ₹1,00,00,000 or less.');
    return exact;
  });
  if (budgets[0] && budgets[1] && BigInt(budgets[0]) > BigInt(budgets[1])) {
    throw new WantedDiscoveryQueryError('Minimum budget must not exceed maximum budget.');
  }
  const rawPage = params.get('page') ?? '1';
  const rawSize = params.get('page_size') ?? '20';
  if (!/^[0-9]+$/.test(rawPage) || !Number.isSafeInteger(Number(rawPage)) || Number(rawPage) < 1) {
    throw new WantedDiscoveryQueryError('The page number cannot be displayed safely. Reset to page 1.');
  }
  if (!['20', '50', '100'].includes(rawSize)) {
    throw new WantedDiscoveryQueryError('Choose 20, 50, or 100 requests per page.');
  }
  const category_code = [...new Set(params.getAll('category_code'))].sort();
  if (category_code.some((value) => !value.trim() || value.length > 100)) {
    throw new WantedDiscoveryQueryError('This Wanted Request link has an invalid category filter.');
  }
  return {
    q,
    category_code,
    min_budget_paise: budgets[0],
    max_budget_paise: budgets[1],
    page: Number(rawPage),
    page_size: Number(rawSize) as WantedDiscoveryQuery['page_size'],
  };
}

/** Keep the two Discovery tabs' independently applied filters in one URL safely. */
export function parseWantedDiscoveryRouteQuery(params: URLSearchParams): WantedDiscoveryQuery {
  const routeKeys = new Set([
    'wanted_q', 'wanted_category_code', 'wanted_min_budget_paise', 'wanted_max_budget_paise',
    'wanted_page', 'wanted_page_size',
  ]);
  if ([...params.keys()].some((key) => key.startsWith('wanted_') && !routeKeys.has(key))) {
    throw new WantedDiscoveryQueryError('This Wanted Request link has invalid filters. Reset the filters and try again.');
  }
  const route = new URLSearchParams();
  for (const [key, apiKey] of [
    ['wanted_q', 'q'],
    ['wanted_category_code', 'category_code'],
    ['wanted_min_budget_paise', 'min_budget_paise'],
    ['wanted_max_budget_paise', 'max_budget_paise'],
    ['wanted_page', 'page'],
    ['wanted_page_size', 'page_size'],
  ] as const) {
    for (const value of params.getAll(key)) route.append(apiKey, value);
  }
  return parseWantedDiscoveryQuery(route);
}

/** Serialize only active filters with sorted, repeated category values. */
export function wantedDiscoveryParams(query: WantedDiscoveryQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set('q', query.q);
  for (const category of [...new Set(query.category_code)].sort()) params.append('category_code', category);
  if (query.min_budget_paise !== '') params.set('min_budget_paise', query.min_budget_paise);
  if (query.max_budget_paise !== '') params.set('max_budget_paise', query.max_budget_paise);
  if (query.page > 1) params.set('page', String(query.page));
  if (query.page_size !== 20) params.set('page_size', String(query.page_size));
  return params;
}

/** Prefix route keys so sale and Wanted filters can coexist without ambiguity. */
export function wantedDiscoveryRouteParams(query: WantedDiscoveryQuery): URLSearchParams {
  const api = wantedDiscoveryParams(query);
  const route = new URLSearchParams();
  const names: Record<string, string> = {
    q: 'wanted_q', category_code: 'wanted_category_code',
    min_budget_paise: 'wanted_min_budget_paise', max_budget_paise: 'wanted_max_budget_paise',
    page: 'wanted_page', page_size: 'wanted_page_size',
  };
  api.forEach((value, key) => route.append(names[key], value));
  return route;
}

/** Convert the applied paise URL values into exact whole-rupee form text. */
export function wantedDiscoveryForm(query: WantedDiscoveryQuery): WantedDiscoveryForm {
  const { min_budget_paise, max_budget_paise, page: _page, ...rest } = query;
  return {
    ...rest,
    min_rupees: min_budget_paise === '' ? '' : (BigInt(min_budget_paise) / 100n).toString(),
    max_rupees: max_budget_paise === '' ? '' : (BigInt(max_budget_paise) / 100n).toString(),
  };
}

/** Validate a whole form at once and reset pagination for changed filters. */
export function applyWantedDiscoveryForm(form: WantedDiscoveryForm): WantedDiscoveryQuery {
  const q = form.q.trim();
  if ([...q].length > 120) throw new WantedDiscoveryQueryError('Search text must be 120 characters or fewer.');
  const min_budget_paise = form.min_rupees.trim()
    ? (BigInt(integerText(form.min_rupees.trim())) * 100n).toString()
    : '';
  const max_budget_paise = form.max_rupees.trim()
    ? (BigInt(integerText(form.max_rupees.trim())) * 100n).toString()
    : '';
  return parseWantedDiscoveryQuery(wantedDiscoveryParams({
    q,
    category_code: [...new Set(form.category_code)].sort(),
    min_budget_paise,
    max_budget_paise,
    page: 1,
    page_size: form.page_size,
  }));
}
