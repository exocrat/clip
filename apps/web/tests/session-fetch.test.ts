import { identityApi } from '../src/features/identity/api';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { sessionFetch, SessionFetchError } from '../src/shared/http/sessionFetch';
const token = 'a'.repeat(64);
const json = (value: unknown, status = 200) => new Response(status === 204 ? null : JSON.stringify(value), { status });
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.useRealTimers(); });

describe('shared app cookie/CSRF transport', () => {
  it.each([['test', '/api/me'], ['identity-preview', '/me']])('routes Identity %s through its explicit API transport', async (mode, expected) => {
    vi.stubEnv('MODE', mode);
    const fetcher = vi.fn().mockResolvedValue(json({ user_id: '11111111-2222-4333-8444-555555555555', account_class: 'regular', valid_until: '2099-01-01T00:00:00.000Z', display_name: null }));
    vi.stubGlobal('fetch', fetcher);
    await identityApi.me();
    expect(fetcher.mock.calls[0][0]).toBe(expected);
  });

  it('reads once through /api without a token request or actor headers', async () => {
    const fetcher = vi.fn().mockResolvedValue(json({ items: [] }));
    vi.stubGlobal('fetch', fetcher);
    expect(await (await sessionFetch('/listings?page=1')).json()).toEqual({ items: [] });
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0][0]).toBe('/api/listings?page=1');
    const init = fetcher.mock.calls[0][1];
    expect(init).toMatchObject({ credentials: 'same-origin', cache: 'no-store', redirect: 'error', mode: 'same-origin', referrerPolicy: 'origin' });
    expect([...new Headers(init.headers)]).toEqual([]);
  });
  it.each(['POST', 'PUT', 'PATCH', 'DELETE'])('preflights one %s and preserves payload/headers with no replay', async (method) => {
    const fetcher = vi.fn().mockImplementation((path: string) => Promise.resolve(path.endsWith('/auth/csrf') ? json({ csrf_token: token }) : json(null, 204)));
    vi.stubGlobal('fetch', fetcher);
    const body = JSON.stringify({ operation_id: 'synthetic-operation' });
    await sessionFetch('/wanted-requests', { method, body, credentials: 'omit', cache: 'force-cache', redirect: 'follow', referrerPolicy: 'no-referrer', headers: [['Content-Type', 'application/json'], ['X-CSRF-Token', 'stale'], ['If-Match', '7']] });
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(fetcher.mock.calls[0][0]).toBe('/api/auth/csrf');
    expect(fetcher.mock.calls[0][1].referrerPolicy).toBe('origin');
    const init = fetcher.mock.calls[1][1];
    expect(init).toMatchObject({ method, body, credentials: 'same-origin', cache: 'no-store', redirect: 'error', mode: 'same-origin', referrerPolicy: 'origin' });
    const headers = new Headers(init.headers);
    expect(headers.get('X-CLIP-Request')).toBe('1');
    expect(headers.get('X-CSRF-Token')).toBe(token);
    expect(headers.get('If-Match')).toBe('7');
    expect(headers.get('Content-Type')).toBe('application/json');
    expect(headers.has('X-User-ID')).toBe(false);
  });
  it.each([401, 403, 404, 503])('never sends the write after CSRF status %s', async (status) => {
    const fetcher = vi.fn().mockResolvedValue(json({ error: 'private detail' }, status));
    vi.stubGlobal('fetch', fetcher);
    await expect(sessionFetch('/listings', { method: 'POST' })).rejects.toMatchObject({ status, mutationDispatched: false });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it.each([{}, null, { csrf_token: 123 }, { csrf_token: '' }, { csrf_token: 'short' }, { csrf_token: 'x'.repeat(129) }, { csrf_token: `${'x'.repeat(32)}\r\n` }, { csrf_token: token, extra: 'private' }])('refuses malformed preflight without sending a write: %j', async (value) => {
    const fetcher = vi.fn().mockResolvedValue(json(value));
    vi.stubGlobal('fetch', fetcher);
    await expect(sessionFetch('/listings', { method: 'POST' })).rejects.toMatchObject({ status: 503, mutationDispatched: false });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('never caches a token and does not repair a session-race 403 by retrying', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(json({ csrf_token: token })).mockResolvedValueOnce(json({}, 403)).mockResolvedValueOnce(json({ csrf_token: 'b'.repeat(64) })).mockResolvedValueOnce(json(null, 204));
    vi.stubGlobal('fetch', fetcher);
    expect((await sessionFetch('/listings', { method: 'POST', body: 'same-operation' })).status).toBe(403);
    expect(fetcher).toHaveBeenCalledTimes(2);
    await sessionFetch('/listings', { method: 'POST', body: 'same-operation' });
    expect(fetcher).toHaveBeenCalledTimes(4);
    expect(new Headers(fetcher.mock.calls[3][1].headers).get('X-CSRF-Token')).toBe('b'.repeat(64));
    expect(fetcher.mock.calls[3][1].body).toBe('same-operation');
  });
  it('does not dispatch after cancellation even when a preflight ignores abort', async () => {
    let resolve: (value: Response) => void = () => undefined;
    const fetcher = vi.fn(() => new Promise<Response>((done) => { resolve = done; }));
    vi.stubGlobal('fetch', fetcher);
    const controller = new AbortController();
    const promise = sessionFetch('/listings', { method: 'POST', signal: controller.signal });
    controller.abort();
    resolve(json({ csrf_token: token }));
    await expect(promise).rejects.toMatchObject({ name: 'AbortError' });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('refuses an already cancelled request before I/O', async () => {
    const fetcher = vi.fn(); vi.stubGlobal('fetch', fetcher);
    const controller = new AbortController(); controller.abort();
    await expect(sessionFetch('/listings', { signal: controller.signal })).rejects.toMatchObject({ name: 'AbortError' });
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('times out preflight without sending a write or exposing failure text', async () => {
    vi.useFakeTimers();
    const fetcher = vi.fn((_path: string, init: RequestInit) => new Promise<Response>((_resolve, reject) => init.signal?.addEventListener('abort', () => reject(new Error('private-network-detail')))));
    vi.stubGlobal('fetch', fetcher);
    const result = expect(sessionFetch('/listings', { method: 'POST' })).rejects.toMatchObject({ status: 503, mutationDispatched: false, message: 'The application request could not be completed safely.' });
    await vi.advanceTimersByTimeAsync(10_000);
    await result;
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  });
  it('keeps cancellation attached while receiving the response body', async () => {
    let body: ReadableStreamDefaultController<Uint8Array>;
    let dispatched: () => void = () => undefined;
    const ready = new Promise<void>((resolve) => { dispatched = resolve; });
    const fetcher = vi.fn((_path: string, init: RequestInit) => {
      const stream = new ReadableStream<Uint8Array>({ start(controller) { body = controller; } });
      init.signal?.addEventListener('abort', () => body.error(new DOMException('cancelled', 'AbortError')));
      dispatched();
      return Promise.resolve(new Response(stream));
    });
    vi.stubGlobal('fetch', fetcher);
    const controller = new AbortController();
    const promise = sessionFetch('/me', { signal: controller.signal });
    await ready; controller.abort();
    await expect(promise).rejects.toMatchObject({ name: 'AbortError' });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it.each(['https://foreign.invalid/path', '//foreign.invalid/path', '/\\foreign.invalid', '/../auth', '/%2e%2e/auth', '/x#fragment', '/x\r\n'])('refuses an unsafe target before I/O: %s', async (path) => {
    const fetcher = vi.fn(); vi.stubGlobal('fetch', fetcher);
    await expect(sessionFetch(path)).rejects.toBeInstanceOf(SessionFetchError);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('allows only reviewed public auth writes without CSRF and supports explicit preview routing', async () => {
    const fetcher = vi.fn().mockResolvedValue(json({})); vi.stubGlobal('fetch', fetcher);
    await sessionFetch('/auth/temporary/sessions', { method: 'POST' }, { publicAuthentication: true, prefix: '' });
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0][0]).toBe('/auth/temporary/sessions');
    expect(new Headers(fetcher.mock.calls[0][1].headers).get('X-CLIP-Request')).toBe('1');
    await expect(sessionFetch('/wanted-requests', { method: 'POST' }, { publicAuthentication: true })).rejects.toBeInstanceOf(SessionFetchError);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});
