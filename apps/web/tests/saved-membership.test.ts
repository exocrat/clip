import { afterEach, describe, expect, it, vi } from 'vitest';
import { isListingSaved } from '../src/features/search/wantedApi';

const savedAt = '2026-10-25T13:00:00.000000Z';
const id = (number: number) => `20000000-0000-4000-8000-${String(number).padStart(12, '0')}`;
const retired = (listingId: string) => ({
  listing_id: listingId,
  saved_at: savedAt,
  listing: null,
  retired: true,
});
const page = (items: unknown[], number: number, hasNext: boolean) => new Response(JSON.stringify({
  items,
  page: number,
  page_size: 100,
  has_next: hasNext,
}), { status: 200, headers: { 'Content-Type': 'application/json' } });

afterEach(() => vi.unstubAllGlobals());

describe('saved listing membership check', () => {
  it('recognizes an already saved listing on the first private page', async () => {
    const fetch = vi.fn().mockResolvedValue(page([retired(id(1))], 1, false));
    vi.stubGlobal('fetch', fetch);

    await expect(isListingSaved(id(1), new AbortController().signal)).resolves.toBe(true);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe('/api/me/saved-listings?page=1&page_size=100');
  });

  it('checks later pages only when earlier pages say more results exist', async () => {
    const first = Array.from({ length: 100 }, (_, index) => retired(id(index + 1)));
    const fetch = vi.fn()
      .mockResolvedValueOnce(page(first, 1, true))
      .mockResolvedValueOnce(page([retired(id(101))], 2, false));
    vi.stubGlobal('fetch', fetch);

    await expect(isListingSaved(id(101), new AbortController().signal)).resolves.toBe(true);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('returns false after the last page when the listing is absent', async () => {
    const fetch = vi.fn().mockResolvedValue(page([], 1, false));
    vi.stubGlobal('fetch', fetch);

    await expect(isListingSaved(id(1), new AbortController().signal)).resolves.toBe(false);
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
