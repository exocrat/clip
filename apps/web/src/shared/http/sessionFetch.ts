/** Cookie-only app transport. CSRF state is per request, never cached or persisted. */
export class SessionFetchError extends Error {
  constructor(readonly status: number, readonly mutationDispatched = false) {
    super('The application request could not be completed safely.');
    this.name = 'SessionFetchError';
  }
}

const safeMethods = new Set(['GET', 'HEAD', 'OPTIONS']);
const methods = new Set([...safeMethods, 'POST', 'PUT', 'PATCH', 'DELETE']);
// Reviewed public authentication operations only; marketplace writes cannot opt out.
const publicAuthentication = new Set([
  '/auth/microsoft/login-attempts',
  '/auth/microsoft/sessions',
  '/auth/temporary/registration-challenges',
  '/auth/temporary/accounts',
  '/auth/temporary/sessions',
  '/auth/temporary/password-reset-challenges',
  '/auth/temporary/password-resets',
]);

export interface SessionFetchPolicy {
  /** Normal Vite/hosted API prefix; empty is for the explicit Identity preview. */
  prefix?: '/api' | '';
  publicAuthentication?: boolean;
}

/** Reject foreign/protocol-relative/normalized traversal targets before any I/O. */
function appPath(path: string): boolean {
  return path.startsWith('/') && !path.startsWith('//') && !path.includes('\\') && !path.includes('#')
    && !Array.from(path).some((character) => character.charCodeAt(0) <= 32 || character.charCodeAt(0) === 127)
    && !path.split('?')[0].split('/').some((part) => /^(?:\.|%2e){1,2}$/i.test(part));
}

/** Fetch fresh session CSRF before each unsafe write, with no automatic replay.
 * Prefix/headers/credentials/cache/redirect policy cannot come from a server reply.
 * A ten-second deadline covers preflight and response receipt; owning JSON validators stay
 * with each feature. The caller's abort propagates through both stages. A session
 * change between stages is denied by the backend, never "repaired" by retrying.
 */
export async function sessionFetch(
  path: string,
  init: RequestInit = {},
  policy: SessionFetchPolicy = {},
): Promise<Response> {
  const prefix = policy.prefix ?? '/api';
  const method = (init.method ?? 'GET').toUpperCase();
  if (!appPath(path) || !['', '/api'].includes(prefix) || !methods.has(method))
    throw new SessionFetchError(503);
  const unsafe = !safeMethods.has(method);
  if (unsafe && policy.publicAuthentication && !publicAuthentication.has(path))
    throw new SessionFetchError(503);
  const controller = new AbortController();
  const cancel = () => controller.abort();
  const parent = init.signal;
  parent?.addEventListener('abort', cancel, { once: true });
  if (parent?.aborted) cancel();
  const timeout = setTimeout(cancel, 10_000);
  let dispatched = false;
  const checkCancellation = () => {
    if (controller.signal.aborted) throw new DOMException('Request cancelled', 'AbortError');
  };
  try {
    checkCancellation();
    const headers = new Headers(init.headers);
    headers.delete('X-CSRF-Token');
    if (unsafe) {
      headers.set('X-CLIP-Request', '1');
      if (!policy.publicAuthentication) {
        const csrf = await fetch(`${prefix}/auth/csrf`, {
          credentials: 'same-origin', cache: 'no-store', mode: 'same-origin',
          redirect: 'error', signal: controller.signal,
          headers: { Accept: 'application/json' },
        });
        if (!csrf.ok) throw new SessionFetchError(csrf.status);
        const value: unknown = await csrf.json();
        if (!value || typeof value !== 'object' || Object.keys(value).length !== 1
          || !('csrf_token' in value) || typeof value.csrf_token !== 'string'
          || !/^[\x21-\x7e]{32,128}$/.test(value.csrf_token))
          throw new SessionFetchError(503);
        checkCancellation();
        headers.set('X-CSRF-Token', value.csrf_token);
      }
    }
    checkCancellation();
    dispatched = unsafe;
    const response = await fetch(`${prefix}${path}`, {
      ...init, method, headers, credentials: 'same-origin', cache: 'no-store',
      mode: 'same-origin', redirect: 'error', signal: controller.signal,
    });
    // App endpoints are bounded JSON/204, never byte uploads or streaming feeds.
    // Finish receiving while abort/deadline are attached; keep the original
    // Response and its metadata/body available to each feature's own validator.
    await response.clone().arrayBuffer();
    return response;
  } catch (error) {
    if (parent?.aborted) {
      if (error instanceof DOMException && error.name === 'AbortError') throw error;
      throw new DOMException('Request cancelled', 'AbortError');
    }
    if (error instanceof SessionFetchError) throw error;
    throw new SessionFetchError(503, dispatched);
  } finally {
    clearTimeout(timeout);
    parent?.removeEventListener('abort', cancel);
  }
}
