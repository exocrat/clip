import { describe, expect, it } from 'vitest';
import {
  applyWantedDiscoveryForm,
  DEFAULT_WANTED_QUERY,
  parseWantedDiscoveryQuery,
  parseWantedDiscoveryRouteQuery,
  wantedDiscoveryForm,
  wantedDiscoveryParams,
  wantedDiscoveryRouteParams,
} from '../src/features/search/wantedDiscoveryQuery';

describe('Wanted Request discovery URL and form state', () => {
  it('round-trips text, repeated categories, budgets and page controls', () => {
    const query = parseWantedDiscoveryQuery(new URLSearchParams(
      'q=physics&category_code=books&category_code=bicycles&min_budget_paise=0&max_budget_paise=250000&page=3&page_size=50',
    ));
    expect(query.category_code).toEqual(['bicycles', 'books']);
    expect(parseWantedDiscoveryQuery(wantedDiscoveryParams(query))).toEqual(query);
    expect(wantedDiscoveryForm(query)).toMatchObject({ min_rupees: '0', max_rupees: '2500' });
  });

  it('applies all draft filters together and resets to page one', () => {
    const form = wantedDiscoveryForm({ ...DEFAULT_WANTED_QUERY, page: 5, page_size: 100 });
    const query = applyWantedDiscoveryForm({
      ...form,
      q: '  physics book  ',
      category_code: ['books', 'bicycles', 'books'],
      min_rupees: '0',
      max_rupees: '9999999',
    });
    expect(query).toMatchObject({
      q: 'physics book', category_code: ['bicycles', 'books'],
      min_budget_paise: '0', max_budget_paise: '999999900',
      page: 1, page_size: 100,
    });
  });

  it('uses empty controls as no restriction and preserves zero budget', () => {
    expect(wantedDiscoveryParams(DEFAULT_WANTED_QUERY).toString()).toBe('');
    expect(wantedDiscoveryForm(DEFAULT_WANTED_QUERY).min_rupees).toBe('');
    const zero = parseWantedDiscoveryQuery(new URLSearchParams('min_budget_paise=0'));
    expect(zero.min_budget_paise).toBe('0');
  });

  it('keeps Wanted URL state separate from sale filters on the shared Discovery route', () => {
    const params = wantedDiscoveryRouteParams({
      ...DEFAULT_WANTED_QUERY,
      q: 'physics',
      category_code: ['books'],
      page: 2,
    });
    expect(params.toString()).toBe('wanted_q=physics&wanted_category_code=books&wanted_page=2');
    const combined = new URLSearchParams('q=bicycle&category_code=bicycles');
    params.forEach((value, key) => combined.append(key, value));
    expect(parseWantedDiscoveryRouteQuery(combined)).toMatchObject({
      q: 'physics', category_code: ['books'], page: 2,
    });
    expect(parseWantedDiscoveryQuery(wantedDiscoveryParams({
      ...DEFAULT_WANTED_QUERY, q: 'physics', category_code: ['books'], page: 2,
    }))).toMatchObject({ q: 'physics', category_code: ['books'], page: 2 });
  });

  it.each([
    'page=0', 'page=-1', 'page=1.5', 'page_size=200', 'q=word&q=other',
    'min_budget_paise=101', 'min_budget_paise=-100', 'max_budget_paise=100.0',
    'min_budget_paise=200&max_budget_paise=100', 'category_code=', 'owner_id=someone',
  ])('rejects invalid or unreviewed query %s', (raw) => {
    expect(() => parseWantedDiscoveryQuery(new URLSearchParams(raw))).toThrow();
  });

  it.each(['1.50', '-1', '1e2', 'not-money'])('rejects non-whole-rupee form input %s', (value) => {
    const form = wantedDiscoveryForm(DEFAULT_WANTED_QUERY);
    expect(() => applyWantedDiscoveryForm({ ...form, min_rupees: value })).toThrow();
  });
});
