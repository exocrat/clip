import { afterEach, describe, expect, it, vi } from 'vitest';
import { discoveryPreviewBackend, readDiscoveryCatalogue, readDiscoveryPage, type ListingSummary, type PageResultListingSummary } from '../src/features/search/discoveryApi';
import { DEFAULT_QUERY } from '../src/features/search/discoveryQuery';

const listing: ListingSummary = { listing_id: '20000000-0000-4000-8000-000000000001', title: 'Synthetic bicycle', description: 'Synthetic fixture',
  category_code: 'bicycles', category_label: 'Bicycles', condition_code: 'good', condition_label: 'Good', asking_price_paise: 100,
  negotiable: false, pickup_area: null, available_from: '2026-01-01T00:00:00.000000Z', available_until: null,
  availability: 'available', sensitive_purchase: false, image_ids: [] };

function page(): PageResultListingSummary { return { items: [{ ...listing }], page: 1, page_size: 20, has_next: false }; }
function stub(value: unknown, status = 200) {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(value), { status }));
  vi.stubGlobal('fetch', fetch);
  return fetch;
}
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

describe('current, public-only discovery transport', () => {
  it('sends only reviewed filters, disables caching and preserves cancellation', async () => {
    const fetch = stub(page());
    const signal = new AbortController().signal;
    await readDiscoveryPage({ ...DEFAULT_QUERY, min_price_paise: '0', negotiable: 'false' }, signal);
    expect(fetch).toHaveBeenCalledWith('/api/listings?min_price_paise=0&negotiable=false', expect.objectContaining({ signal, cache: 'no-store', credentials: 'same-origin' }));
    expect(JSON.stringify(fetch.mock.calls)).not.toMatch(/owner_id|user_id|Authorization|X-Clip-UI-Preview/);
  });
  it('enables the preview transport header only with explicit development opt-in', async () => {
    vi.stubEnv('VITE_SEARCH_UI_PREVIEW', 'true');
    const fetch = stub(page());
    await readDiscoveryPage(DEFAULT_QUERY, new AbortController().signal);
    expect(fetch.mock.calls[0][1].headers).toMatchObject({ 'X-Clip-UI-Preview': 'search-fixtures' });
  });
  it.each([401, 403, 422, 429, 503])('preserves status %s without reflecting provider diagnostics or retrying', async (status) => {
    const fetch = stub({ private_diagnostic: 'synthetic-private-provider-detail' }, status);
    await expect(readDiscoveryPage(DEFAULT_QUERY, new AbortController().signal)).rejects.toMatchObject({ status });
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it.each(['private-extra', 'unavailable', 'unsafe-money', 'duplicate-id', 'wrong-page', 'false-lookahead'])('rejects malformed public result %s', async (kind) => {
    const value = JSON.parse(JSON.stringify(page())) as Record<string, unknown>;
    const items = value.items as Record<string, unknown>[];
    if (kind === 'private-extra') items[0].owner_id = 'synthetic-private';
    if (kind === 'unavailable') items[0].availability = 'unavailable';
    if (kind === 'unsafe-money') items[0].asking_price_paise = Number.MAX_SAFE_INTEGER + 1;
    if (kind === 'duplicate-id') items.push({ ...items[0] });
    if (kind === 'wrong-page') value.page = 2;
    if (kind === 'false-lookahead') value.has_next = true;
    stub(value);
    await expect(readDiscoveryPage(DEFAULT_QUERY, new AbortController().signal)).rejects.toMatchObject({ status: 0 });
  });
  it('keeps cancellation distinct from a visible network failure', async () => {
    const controller = new AbortController();
    controller.abort();
    const error = new DOMException('Synthetic abort', 'AbortError');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error));
    await expect(readDiscoveryPage(DEFAULT_QUERY, controller.signal)).rejects.toBe(error);
  });
  it('rejects malformed JSON safely', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('synthetic-private-non-json')));
    await expect(readDiscoveryPage(DEFAULT_QUERY, new AbortController().signal)).rejects.not.toThrow('synthetic-private');
  });
  it('reads active catalogue shapes and refuses duplicate options', async () => {
    const value = { categories: [{ code: 'bicycles', label: 'Bicycles' }], conditions: [{ code: 'good', label: 'Good' }] };
    stub(value);
    await expect(readDiscoveryCatalogue(new AbortController().signal)).resolves.toEqual(value);
    stub({ ...value, categories: [value.categories[0], value.categories[0]] });
    await expect(readDiscoveryCatalogue(new AbortController().signal)).rejects.toMatchObject({ status: 0 });
  });
});


describe('development backend disclosure', () => {
  it.each([['search-native-model-synthetic-identity', 'native'], ['search-ui-fixtures', 'fixtures'], ['unknown', 'unknown']] as const)('identifies %s from response metadata without changing routing', async (header, expected) => {
    vi.stubEnv('VITE_SEARCH_UI_PREVIEW', 'true');
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(page()), { headers: { 'X-Clip-Preview': header } }));
    vi.stubGlobal('fetch', fetch);
    await readDiscoveryPage(DEFAULT_QUERY, new AbortController().signal);
    expect(discoveryPreviewBackend()).toBe(expected);
    expect(fetch.mock.calls[0][0]).toBe('/api/listings');
  });
});
