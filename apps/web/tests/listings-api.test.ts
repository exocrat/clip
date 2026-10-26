import { withCsrf } from './helpers/csrf';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  changeListingAvailability,
  createListing,
  listingsRequest,
  readMyListings,
  type AvailabilityChange,
  type CreateListingRequest,
} from '../src/features/listings/listingsApi';

afterEach(() => vi.unstubAllGlobals());

describe('Listings HTTP failures and write retries', () => {
  it.each([new Headers({ 'If-Match': '7' }), [['If-Match', '7']] as [string, string][]])('preserves standard RequestInit header forms', async (headers) => {
    const fetch = vi.fn().mockResolvedValue(new Response('{}'));
    vi.stubGlobal('fetch', withCsrf(fetch));
    await listingsRequest('/catalogue', { headers });
    const sent = new Headers(fetch.mock.calls[0][1].headers);
    expect(sent.get('If-Match')).toBe('7');
    expect(sent.get('Content-Type')).toBe('application/json');
  });

  it('does not display raw failed-response diagnostics or automatically retry a write', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response('private provider diagnostic', { status: 503 }));
    vi.stubGlobal('fetch', withCsrf(fetch));
    await expect(createListing({ operation_id: 'synthetic-key' } as CreateListingRequest)).rejects.toThrow('A required service is unavailable');
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][1].body).toContain('synthetic-key');
  });
  it('turns malformed JSON into a safe retry message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('private non-JSON response', { status: 200 })));
    await expect(listingsRequest('/catalogue')).rejects.toThrow('The request could not be completed. Please try again.');
  });
  it('keeps the caller-supplied cancellation signal and sends no actor ID/header', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', withCsrf(fetch));
    const controller = new AbortController();
    await listingsRequest('/catalogue', { signal: controller.signal });
    expect(fetch).toHaveBeenCalledWith('/api/catalogue', expect.objectContaining({
      signal: expect.any(AbortSignal), credentials: 'same-origin', headers: expect.any(Headers),
    }));
  });
  it('loads the current account listings through the server-owned identity boundary', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      items: [], page: 2, page_size: 20, has_next: false,
    }), { status: 200 }));
    vi.stubGlobal('fetch', withCsrf(fetch));
    const controller = new AbortController();
    await expect(readMyListings(2, controller.signal)).resolves.toEqual({
      items: [], page: 2, page_size: 20, has_next: false,
    });
    expect(fetch).toHaveBeenCalledWith('/api/me/listings?page=2', expect.objectContaining({
      signal: expect.any(AbortSignal),
      credentials: 'same-origin',
    }));
    expect(new Headers(fetch.mock.calls[0][1].headers).get('X-User-ID')).toBeNull();
    expect(JSON.stringify(fetch.mock.calls[0][1])).not.toMatch(/owner_id|user_id|account_id/i);
  });
  it('changes availability through the owner route with the current revision and stable operation key', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ listing_id: 'listing-id' }), { status: 200 }));
    vi.stubGlobal('fetch', withCsrf(fetch));
    await changeListingAvailability('listing/one', {
      expected_revision: 7,
      availability: 'unavailable',
      available_from: '2026-10-22T10:00:00Z',
      available_until: null,
      operation_id: 'operation-id',
    } satisfies AvailabilityChange);
    expect(fetch).toHaveBeenCalledWith('/api/listings/listing%2Fone/availability', expect.objectContaining({
      method: 'PUT',
      body: JSON.stringify({
        expected_revision: 7,
        availability: 'unavailable',
        available_from: '2026-10-22T10:00:00Z',
        available_until: null,
        operation_id: 'operation-id',
      }),
    }));
  });
});
