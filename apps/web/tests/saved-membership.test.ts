import { afterEach, describe, expect, it, vi } from 'vitest';
import { isListingSaved } from '../src/features/search/wantedApi';

const id = (n: number) => `20000000-0000-4000-8000-${String(n).padStart(12, '0')}`;
const response = (items: unknown[]) => new Response(JSON.stringify({ items }), {
  status: 200, headers: { 'Content-Type': 'application/json' },
});
afterEach(() => vi.unstubAllGlobals());

describe('private saved membership batching', () => {
  it('checks an entire render in one request without loading saved listing content', async () => {
    const fetch = vi.fn().mockResolvedValue(response([
      { listing_id: id(1), saved: true }, { listing_id: id(2), saved: false },
    ]));
    vi.stubGlobal('fetch', fetch);
    await expect(Promise.all([isListingSaved(id(1)), isListingSaved(id(2)), isListingSaved(id(1))]))
      .resolves.toEqual([true, false, true]);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe(`/api/me/saved-listings/status?listing_ids=${id(1)}&listing_ids=${id(2)}`);
  });

  it('rejects incomplete or foreign membership responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response([{ listing_id: id(9), saved: true }])));
    await expect(isListingSaved(id(1))).rejects.toThrow();
  });

  it('does not reuse membership after a navigation or account change', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(response([{ listing_id: id(1), saved: true }]))
      .mockResolvedValueOnce(response([{ listing_id: id(1), saved: false }]));
    vi.stubGlobal('fetch', fetch);
    await expect(isListingSaved(id(1))).resolves.toBe(true);
    await expect(isListingSaved(id(1))).resolves.toBe(false);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('cancels an unmounted caller while preserving another card in the same batch', async () => {
    const removed = new AbortController();
    vi.stubGlobal('fetch', vi.fn().mockImplementation((_path, options) =>
      new Promise((resolve) => {
        removed.abort();
        expect(options.signal.aborted).toBe(false);
        resolve(response([{ listing_id: id(1), saved: true }, { listing_id: id(2), saved: false }]));
      }),
    ));
    const abandoned = isListingSaved(id(1), removed.signal);
    const retained = isListingSaved(id(2));
    await expect(abandoned).rejects.toMatchObject({ name: 'AbortError' });
    await expect(retained).resolves.toBe(false);
  });
});
