import { describe, expect, it } from 'vitest';
import { applyDiscoveryForm, DEFAULT_QUERY, discoveryForm, discoveryParams, editDiscoveryText, parseDiscoveryQuery, switchDiscoveryMode } from '../src/features/search/discoveryQuery';

describe('reviewed discovery URL and form boundary', () => {
  it('round-trips applied filters while preserving zero and the selected page', () => {
    const query = parseDiscoveryQuery(new URLSearchParams('q=+bicycle+&category_code=bicycles&category_code=books&condition_code=good&condition_code=like_new&min_price_paise=0&max_price_paise=10000&sort=price_asc&page=3&page_size=50'));
    expect(query.q).toBe('bicycle');
    expect(query.min_price_paise).toBe('0');
    expect(parseDiscoveryQuery(discoveryParams(query))).toEqual(query);
    expect(query.category_code).toEqual(['bicycles', 'books']);
    expect(query.condition_code).toEqual(['good', 'like_new']);
  });
  it('converts whole rupees exactly and resets page after applying controls', () => {
    const form = discoveryForm({ ...DEFAULT_QUERY, page: 7, page_size: 100 });
    const query = applyDiscoveryForm({ ...form, min_rupees: '0', max_rupees: '9999999' });
    expect(query.page).toBe(1);
    expect(query.max_price_paise).toBe('999999900');
    expect(query.min_price_paise).toBe('0');
    expect(discoveryForm(query).max_rupees).toBe('9999999');
  });
  it('omits unset filters/defaults without turning an absent price into zero', () => {
    expect(discoveryParams(DEFAULT_QUERY).toString()).toBe('');
    expect(discoveryForm(DEFAULT_QUERY).min_rupees).toBe('');
    expect(parseDiscoveryQuery(new URLSearchParams()).page).toBe(1);
    expect(parseDiscoveryQuery(new URLSearchParams()).search_mode).toBe('hybrid');
    expect(applyDiscoveryForm(discoveryForm(DEFAULT_QUERY)).search_mode).toBe('hybrid');
  });
  it('ignores a legacy negotiability URL filter and never writes it back', () => {
    const query = parseDiscoveryQuery(new URLSearchParams('negotiable=false&q=bicycle'));
    expect(query.q).toBe('bicycle');
    expect(discoveryParams(query).has('negotiable')).toBe(false);
  });
  it('defaults searches to automatic matches but preserves an explicit newest-first choice', () => {
    const searched = parseDiscoveryQuery(new URLSearchParams('q=bicycle'));
    expect(searched.sort).toBe('relevance');
    expect(searched.sort_explicit).toBe(false);
    expect(parseDiscoveryQuery(discoveryParams(searched))).toEqual(searched);
    const newest = parseDiscoveryQuery(new URLSearchParams('q=bicycle&sort=created_desc'));
    expect(newest.sort).toBe('created_desc');
    expect(newest.sort_explicit).toBe(true);
    expect(parseDiscoveryQuery(discoveryParams(newest))).toEqual(newest);
    const form = { ...discoveryForm(DEFAULT_QUERY), q: 'bicycle' };
    expect(applyDiscoveryForm(form).sort).toBe('relevance');
    expect(applyDiscoveryForm({ ...form, sort: 'created_desc', sort_explicit: true }).sort).toBe('created_desc');
    const explicitBestMatch = parseDiscoveryQuery(new URLSearchParams('q=bicycle&sort=relevance'));
    expect(explicitBestMatch.sort_explicit).toBe(true);
    expect(parseDiscoveryQuery(discoveryParams(explicitBestMatch))).toEqual(explicitBestMatch);
  });
  it('accepts the ₹1 crore filter boundary and rejects larger amounts', () => {
    expect(parseDiscoveryQuery(new URLSearchParams('min_price_paise=1000000000')).min_price_paise).toBe('1000000000');
    expect(() => parseDiscoveryQuery(new URLSearchParams('max_price_paise=1000000100'))).toThrow();
  });
  it('keeps a chosen sort while refining filters, but resets it when search text changes', () => {
    const selected = parseDiscoveryQuery(new URLSearchParams('q=vehicle&sort=price_asc'));
    const form = discoveryForm(selected);
    expect(applyDiscoveryForm({ ...form, min_rupees: '100' }).sort).toBe('price_asc');
    const nextSearch = editDiscoveryText(form, 'bicycle');
    expect(nextSearch.sort).toBe('relevance');
    expect(nextSearch.sort_explicit).toBe(false);
    expect(applyDiscoveryForm(nextSearch).sort).toBe('relevance');
    expect(editDiscoveryText(nextSearch, '').sort).toBe('created_desc');
  });
  it('counts Unicode code points after trimming', () => {
    expect(parseDiscoveryQuery(new URLSearchParams({ q: ` ${'🙂'.repeat(120)} ` })).q).toBe('🙂'.repeat(120));
    expect(() => parseDiscoveryQuery(new URLSearchParams({ q: '🙂'.repeat(121) }))).toThrow();
  });
  it.each(['page=0', 'page=-1', 'page=1.5', 'page=9007199254740992', 'page_size=200',
    'sort=unsafe', 'negotiable=maybe', 'min_price_paise=101', 'min_price_paise=-100',
    'max_price_paise=100.0', 'min_price_paise=200&max_price_paise=100', 'q=one&q=two',
    'owner_id=synthetic', 'user_id=synthetic'])('refuses invalid or actor-selecting URL %s', (raw) => {
    expect(() => parseDiscoveryQuery(new URLSearchParams(raw))).toThrow();
  });
  it('deduplicates repeated category and condition values but rejects repeated single-choice fields', () => {
    const query = parseDiscoveryQuery(new URLSearchParams('category_code=books&category_code=books&condition_code=good&condition_code=good'));
    expect(query.category_code).toEqual(['books']);
    expect(query.condition_code).toEqual(['good']);
    expect(() => parseDiscoveryQuery(new URLSearchParams('sort=created_desc&sort=price_asc'))).toThrow();
  });
  it.each(['-1', '1.50', '1e2', 'Infinity', 'not-money'])('never rounds invalid rupees %s', (value) => {
    expect(() => applyDiscoveryForm({ ...discoveryForm(DEFAULT_QUERY), min_rupees: value })).toThrow();
  });
});


describe('mode and relevance URL/form transitions', () => {
  it.each(['keyword', 'hybrid'] as const)('round-trips relevance in %s and defaults to newest', (mode) => {
    const applied = { ...DEFAULT_QUERY, q: 'vehicle', search_mode: mode, sort: 'relevance' as const, page: 3, page_size: 100 as const };
    expect(parseDiscoveryQuery(discoveryParams(applied))).toEqual(applied);
    expect(parseDiscoveryQuery(new URLSearchParams({ search_mode: mode })).sort).toBe('created_desc');
    expect(parseDiscoveryQuery(new URLSearchParams({ search_mode: mode, q: 'vehicle' })).sort).toBe('relevance');
    expect(discoveryParams(applied).has('search_mode')).toBe(mode === 'keyword');
  });
  it.each(['search_mode=', 'search_mode=Hybrid', 'search_mode=semantic', 'search_mode=keyword&search_mode=hybrid',
    'sort=relevance', 'q=+&sort=relevance&search_mode=hybrid'])('rejects invalid manual URL %s', (raw) => {
    expect(() => parseDiscoveryQuery(new URLSearchParams(raw))).toThrow();
  });
  it('switches only applied inputs, preserves filters/sort/size, resets page and leaves drafts intact', () => {
    const applied = { ...DEFAULT_QUERY, search_mode: 'keyword' as const, q: 'bicycle', min_price_paise: '0', sort: 'relevance' as const, page_size: 50 as const, page: 3 };
    const draft = { ...discoveryForm(applied), q: 'desk', max_rupees: '500' };
    const switched = switchDiscoveryMode(applied, 'hybrid');
    expect(switched).toEqual({ ...applied, search_mode: 'hybrid', page: 1 });
    expect(draft.q).toBe('desk');
    expect(switchDiscoveryMode(switched, 'keyword')).toEqual({ ...applied, page: 1 });
    expect(applyDiscoveryForm(draft, switched.search_mode)).toEqual({ ...switched, q: 'desk', max_price_paise: '50000' });
  });
  it.each(['keyword', 'hybrid'] as const)('clearing a relevance form selects newest in %s; manual URL remains invalid', (mode) => {
    const form = { ...discoveryForm(DEFAULT_QUERY), q: '  ', sort: 'relevance' as const };
    expect(applyDiscoveryForm(form, mode)).toEqual({ ...DEFAULT_QUERY, search_mode: mode });
    expect(() => parseDiscoveryQuery(new URLSearchParams({ sort: 'relevance', search_mode: mode }))).toThrow();
  });
});
