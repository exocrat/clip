import { afterEach, describe, expect, it, vi } from 'vitest';
import { DiscoveryApiError, readDiscoveryCatalogue, readDiscoveryPage, type PageResultListingSummary } from '../src/features/search/discoveryApi';
import { DEFAULT_QUERY } from '../src/features/search/discoveryQuery';
import { startDiscoveryRequest } from '../src/features/search/discoveryRequest';

vi.mock('../src/features/search/discoveryApi', async (original) => {
  const actual = await original<typeof import('../src/features/search/discoveryApi')>();
  return { ...actual, readDiscoveryCatalogue: vi.fn(), readDiscoveryPage: vi.fn() };
});
const catalogue = { categories: [], conditions: [] };
const page: PageResultListingSummary = { items: [], page: 1, page_size: 20, has_next: false };
const flush = async () => { await new Promise<void>((resolve) => setImmediate(resolve)); };
afterEach(() => vi.resetAllMocks());

describe('current-only discovery requests', () => {
  it('aborts an old request and ignores its success even if transport ignores cancellation', async () => {
    let finishOld: (value: typeof page) => void = () => { throw new Error('Not initialized'); };
    vi.mocked(readDiscoveryCatalogue).mockResolvedValue(catalogue);
    vi.mocked(readDiscoveryPage).mockImplementationOnce(() => new Promise((resolve) => { finishOld = resolve; })).mockResolvedValueOnce(page);
    const oldReady = vi.fn(); const oldError = vi.fn(); const newReady = vi.fn();
    const cancelOld = startDiscoveryRequest(DEFAULT_QUERY, oldReady, oldError);
    const oldSignal = vi.mocked(readDiscoveryPage).mock.calls[0][1];
    cancelOld();
    const hybrid = { ...DEFAULT_QUERY, q: 'vehicle', search_mode: 'hybrid' as const };
    const cancelNew = startDiscoveryRequest(hybrid, newReady, vi.fn());
    await flush();
    finishOld(page); await flush();
    expect(oldSignal.aborted).toBe(true);
    expect(oldReady).not.toHaveBeenCalled(); expect(oldError).not.toHaveBeenCalled();
    expect(newReady).toHaveBeenCalledExactlyOnceWith(catalogue, page);
    expect(readDiscoveryPage).toHaveBeenLastCalledWith(hybrid, expect.any(AbortSignal));
    cancelNew();
  });
  it('ignores late errors after a mode change or unmount', async () => {
    let rejectOld: (error: Error) => void = () => { throw new Error('Not initialized'); };
    vi.mocked(readDiscoveryCatalogue).mockResolvedValue(catalogue);
    vi.mocked(readDiscoveryPage).mockImplementation(() => new Promise((_resolve, reject) => { rejectOld = reject; }));
    const failed = vi.fn(); const ready = vi.fn();
    const cancel = startDiscoveryRequest(DEFAULT_QUERY, ready, failed);
    cancel(); rejectOld(new DiscoveryApiError(503)); await flush();
    expect(failed).not.toHaveBeenCalled(); expect(ready).not.toHaveBeenCalled();
  });
  it('reports Hybrid503 without success/fallback; retry resends the same applied query', async () => {
    vi.mocked(readDiscoveryCatalogue).mockResolvedValue(catalogue);
    vi.mocked(readDiscoveryPage).mockRejectedValueOnce(new DiscoveryApiError(503)).mockResolvedValueOnce(page);
    const query = { ...DEFAULT_QUERY, q: 'hybrid-down', search_mode: 'hybrid' as const };
    const ready = vi.fn(); const failed = vi.fn();
    const cancel = startDiscoveryRequest(query, ready, failed); await flush();
    expect(failed.mock.calls[0][0].status).toBe(503); expect(ready).not.toHaveBeenCalled();
    expect(readDiscoveryPage).toHaveBeenCalledTimes(1);
    expect(vi.mocked(readDiscoveryCatalogue).mock.calls[0][0].aborted).toBe(true);
    cancel();
    const cancelRetry = startDiscoveryRequest(query, ready, failed); await flush();
    expect(vi.mocked(readDiscoveryPage).mock.calls.map(([applied]) => applied)).toEqual([query, query]);
    expect(ready).toHaveBeenCalledExactlyOnceWith(catalogue, page); cancelRetry();
  });
  it('does not expose a page if its catalogue fails', async () => {
    vi.mocked(readDiscoveryCatalogue).mockRejectedValue(new DiscoveryApiError(403));
    vi.mocked(readDiscoveryPage).mockResolvedValue(page);
    const ready = vi.fn(); const failed = vi.fn();
    const cancel = startDiscoveryRequest(DEFAULT_QUERY, ready, failed); await flush();
    expect(ready).not.toHaveBeenCalled(); expect(failed.mock.calls[0][0].status).toBe(403); cancel();
  });
});
