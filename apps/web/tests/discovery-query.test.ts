import { describe, expect, it } from 'vitest';
import { applyDiscoveryForm, DEFAULT_QUERY, discoveryForm, discoveryParams, parseDiscoveryQuery, switchDiscoveryMode } from '../src/features/search/discoveryQuery';

describe('reviewed discovery URL and form boundary', () => {
  it('round-trips applied filters while preserving zero, false and the selected page', () => {
    const query = parseDiscoveryQuery(new URLSearchParams('q=+bicycle+&category_code=bicycles&condition_code=good&min_price_paise=0&max_price_paise=10000&negotiable=false&sort=price_asc&page=3&page_size=50'));
    expect(query.q).toBe('bicycle');
    expect(query.negotiable).toBe('false');
    expect(query.min_price_paise).toBe('0');
    expect(parseDiscoveryQuery(discoveryParams(query))).toEqual(query);
  });
  it('converts whole rupees exactly and resets page after applying controls', () => {
    const form = discoveryForm({ ...DEFAULT_QUERY, page: 7, page_size: 100, negotiable: 'false' });
    const query = applyDiscoveryForm({ ...form, min_rupees: '0', max_rupees: '900719925474099100' });
    expect(query.page).toBe(1);
    expect(query.max_price_paise).toBe('90071992547409910000');
    expect(query.min_price_paise).toBe('0');
    expect(discoveryForm(query).max_rupees).toBe('900719925474099100');
  });
  it('omits unset filters/defaults without turning an absent price into zero', () => {
    expect(discoveryParams(DEFAULT_QUERY).toString()).toBe('');
    expect(discoveryForm(DEFAULT_QUERY).min_rupees).toBe('');
    expect(parseDiscoveryQuery(new URLSearchParams()).page).toBe(1);
    expect(parseDiscoveryQuery(new URLSearchParams()).search_mode).toBe('hybrid');
    expect(applyDiscoveryForm(discoveryForm(DEFAULT_QUERY)).search_mode).toBe('hybrid');
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
  it.each(['-1', '1.50', '1e2', 'Infinity', 'not-money'])('never rounds invalid rupees %s', (value) => {
    expect(() => applyDiscoveryForm({ ...discoveryForm(DEFAULT_QUERY), min_rupees: value })).toThrow();
  });
});


describe('mode and relevance URL/form transitions', () => {
  it.each(['keyword', 'hybrid'] as const)('round-trips relevance in %s and defaults to newest', (mode) => {
    const applied = { ...DEFAULT_QUERY, q: 'vehicle', search_mode: mode, sort: 'relevance' as const, page: 3, page_size: 100 as const };
    expect(parseDiscoveryQuery(discoveryParams(applied))).toEqual(applied);
    expect(parseDiscoveryQuery(new URLSearchParams({ search_mode: mode })).sort).toBe('created_desc');
    expect(discoveryParams(applied).has('search_mode')).toBe(mode === 'keyword');
  });
  it.each(['search_mode=', 'search_mode=Hybrid', 'search_mode=semantic', 'search_mode=keyword&search_mode=hybrid',
    'sort=relevance', 'q=+&sort=relevance&search_mode=hybrid'])('rejects invalid manual URL %s', (raw) => {
    expect(() => parseDiscoveryQuery(new URLSearchParams(raw))).toThrow();
  });
  it('switches only applied inputs, preserves filters/sort/size, resets page and leaves drafts intact', () => {
    const applied = { ...DEFAULT_QUERY, search_mode: 'keyword' as const, q: 'bicycle', negotiable: 'false' as const, min_price_paise: '0', sort: 'relevance' as const, page_size: 50 as const, page: 3 };
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
