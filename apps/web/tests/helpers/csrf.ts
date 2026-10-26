/** Reviewed synthetic token response for feature tests whose assertions concern
 * business requests. Shared transport tests separately inspect the full preflight
 * sequence and denial behavior; this fixture never enters an application build. */
export const csrfToken = 'c'.repeat(64);
export function withCsrf(fetcher: (path: string, init: RequestInit) => Promise<Response>) {
  return (path: string, init: RequestInit): Promise<Response> => {
    if (path === '/api/auth/csrf')
      return Promise.resolve(new Response(JSON.stringify({ csrf_token: csrfToken }), {
        headers: { 'Cache-Control': 'no-store' },
      }));
    return fetcher(path, init);
  };
}
