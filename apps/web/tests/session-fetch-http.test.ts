import { afterEach, describe, expect, it, vi } from 'vitest';
import { identityApi } from '../src/features/identity/api';
import { changeListingAvailability } from '../src/features/listings/listingsApi';
import { createWanted, editWanted, ownWanted } from '../src/features/search/wantedApi';

/** Python owns the loopback server/SQL and supplies only transient synthetic cookies.
 * The bridge emulates browser Origin/cookie handling and the Vite /api rewrite.
 * Actual fetch, shared TS adapters, Identity middleware and domain SQL run here;
 * browser/device/provider acceptance remains separate. Nothing is persisted. */
const raw = process.env.CLIP_IDENTITY_TRANSPORT_HTTP;
describe.skipIf(!raw)('real cookie/CSRF client-to-shared-API integration', () => {
  afterEach(() => vi.unstubAllGlobals());
  it('writes both domains, rejects stale/missing proof and stops after logout', async () => {
    const config = JSON.parse(raw ?? '{}') as { port: number; regularCookie: string; temporaryCookie: string; listingId: string };
    expect(Number.isInteger(config.port) && config.port > 0 && config.port <= 65535).toBe(true);
    const realFetch = globalThis.fetch;
    let cookie = config.regularCookie;
    let rotateAfterCsrf = false;
    const calls: { path: string; method: string }[] = [];
    const browserFetch = async (path: string, options: RequestInit = {}) => {
      expect(path.startsWith('/api/')).toBe(true);
      const headers = new Headers(options.headers);
      headers.set('Origin', 'http://localhost:5173');
      headers.set('Cookie', `clip_session_dev=${cookie}`);
      calls.push({ path, method: options.method ?? 'GET' });
      const response = await realFetch(`http://127.0.0.1:${config.port}${path.slice(4)}`, { ...options, headers });
      for (const value of response.headers.getSetCookie()) {
        const pair = value.split(';')[0];
        if (pair.startsWith('clip_session_dev=')) cookie = pair.slice('clip_session_dev='.length);
      }
      if (rotateAfterCsrf && path === '/api/auth/csrf') { cookie = config.temporaryCookie; rotateAfterCsrf = false; }
      return response;
    };
    vi.stubGlobal('fetch', browserFetch);
    const signal = () => new AbortController().signal;
    const fields = { title: 'Synthetic browser wanted', description: 'Owned transport fixture only.', category_code: 'books', operation_id: crypto.randomUUID() };
    const wanted = await createWanted(fields, signal());
    const edited = await editWanted(wanted.request_id, { expected_revision: wanted.revision, title: 'Synthetic browser updated', operation_id: crypto.randomUUID() }, signal());
    expect(edited.title).toBe('Synthetic browser updated');
    expect((await ownWanted(1, signal())).items).toHaveLength(1);
    const listing = await changeListingAvailability(config.listingId, { expected_revision: 1, availability: 'unavailable', available_until: null, operation_id: crypto.randomUUID() });
    expect(listing.availability).toBe('unavailable');
    expect('revision' in listing).toBe(false);
    cookie = config.temporaryCookie;
    expect((await createWanted({ ...fields, operation_id: crypto.randomUUID() }, signal())).title).toBe(fields.title);
    await expect(changeListingAvailability(config.listingId, { expected_revision: 2, availability: 'available', available_until: null, operation_id: crypto.randomUUID() })).rejects.toMatchObject({ status: 403 });
    cookie = config.regularCookie;
    rotateAfterCsrf = true;
    const beforeRace = calls.length;
    await expect(createWanted({ ...fields, operation_id: crypto.randomUUID() }, signal())).rejects.toMatchObject({ status: 403 });
    expect(calls.length - beforeRace).toBe(2);
    cookie = config.regularCookie;
    const noProof = await browserFetch('/api/wanted-requests', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CLIP-Request': '1' }, body: JSON.stringify({ ...fields, operation_id: crypto.randomUUID() }) });
    expect(noProof.status).toBe(403);
    await identityApi.logout();
    const beforeLogoutFailure = calls.length;
    await expect(createWanted({ ...fields, operation_id: crypto.randomUUID() }, signal())).rejects.toMatchObject({ status: 401 });
    expect(calls.length - beforeLogoutFailure).toBe(1);
    expect(calls.at(-1)?.path).toBe('/api/auth/csrf');
  });
});
