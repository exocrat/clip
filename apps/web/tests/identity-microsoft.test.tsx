// @vitest-environment jsdom
import { StrictMode } from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  initialize: vi.fn(),
  redirect: vi.fn(),
  handle: vi.fn(),
  clear: vi.fn(),
  configurations: [] as unknown[],
}));
vi.mock('@azure/msal-browser', () => ({
  PublicClientApplication: class {
    constructor(configuration: unknown) {
      mocks.configurations.push(configuration);
    }
    initialize = mocks.initialize;
    loginRedirect = mocks.redirect;
    handleRedirectPromise = mocks.handle;
    clearCache = mocks.clear;
  },
  BrowserCacheLocation: { SessionStorage: 'sessionStorage' },
  LogLevel: { Error: 0 },
}));
const nonce = 'synthetic-server-nonce-value-for-sdk-fixture-only';
const customState = '11111111-2222-4333-8444-555555555555';
const view = {
  user_id: 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee',
  account_class: 'regular',
  valid_until: '2100-01-01T00:00:00.000000Z',
  display_name: null,
};
const assertion = 'synthetic-id-assertion-do-not-send';
function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}
function fetcher(handler: (path: string, init: RequestInit) => Response | Promise<Response>) {
  const mock = vi.fn((path: string, init: RequestInit) => Promise.resolve(handler(path, init)));
  vi.stubGlobal('fetch', mock);
  return mock;
}
function marker(expiresAt = new Date(Date.now() + 600_000).toISOString()) {
  sessionStorage.setItem(
    'clip.microsoft.redirect',
    JSON.stringify({ state: customState, nonce, expiresAt }),
  );
}
function sdkResult(change = {}) {
  return { state: customState, idToken: assertion, idTokenClaims: { nonce }, ...change };
}
async function flow() {
  return import('../src/features/identity/microsoft');
}

beforeEach(() => {
  vi.resetModules();
  vi.clearAllMocks();
  mocks.configurations.length = 0;
  vi.stubEnv('VITE_MICROSOFT_SIGN_IN_ENABLED', 'true');
  vi.stubEnv('MODE', 'test');
  window.history.replaceState(null, '', '/auth/callback');
  sessionStorage.clear();
  localStorage.clear();
  mocks.initialize.mockResolvedValue(undefined);
  mocks.redirect.mockResolvedValue(undefined);
  mocks.handle.mockResolvedValue(sdkResult());
  mocks.clear.mockResolvedValue(undefined);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
  sessionStorage.clear();
  window.history.replaceState(null, '', '/');
});

describe('Microsoft redirect controller with a controlled SDK port', () => {
  it('uses reviewed config/server nonce and stores only bounded public handshake metadata', async () => {
    const fetch = fetcher(() =>
      response({ nonce, expires_at: new Date(Date.now() + 600_000).toISOString() }),
    );
    window.history.replaceState(null, '', '/sign-in');
    const controller = await flow();
    await controller.beginMicrosoft();
    expect(fetch.mock.calls.map((row) => row[0])).toEqual(['/api/auth/microsoft/login-attempts']);
    expect(fetch.mock.calls[0][1]).toMatchObject({
      method: 'POST',
      credentials: 'same-origin',
      headers: expect.any(Headers),
    });
    expect(new Headers(fetch.mock.calls[0][1].headers).get('X-CLIP-Request')).toBe('1');
    expect(mocks.configurations[0]).toMatchObject({
      auth: {
        clientId: controller.MICROSOFT_CLIENT_ID,
        authority: 'https://login.microsoftonline.com/common',
        redirectUri: 'http://localhost:5173/auth/callback',
      },
      cache: { cacheLocation: 'sessionStorage', cacheRetentionDays: 0 },
      system: {
        allowPlatformBroker: false,
        serverTelemetryEnabled: false,
        loggerOptions: { piiLoggingEnabled: false },
      },
    });
    const stored = JSON.parse(sessionStorage.getItem(controller.MICROSOFT_ATTEMPT_KEY) ?? '{}');
    expect(Object.keys(stored).sort()).toEqual(['expiresAt', 'nonce', 'state']);
    expect(stored.nonce).toBe(nonce);
    expect(stored).not.toHaveProperty('id_token');
    expect(localStorage.length).toBe(0);
    expect(mocks.redirect).toHaveBeenCalledWith({
      scopes: ['openid', 'profile', 'email'],
      nonce,
      state: stored.state,
      prompt: 'select_account',
    });
  });

  it.each(['disabled', 'preview'])(
    'fails closed in %s without initializing SDK or contacting provider',
    async (mode) => {
      if (mode === 'disabled') vi.stubEnv('VITE_MICROSOFT_SIGN_IN_ENABLED', 'false');
      else vi.stubEnv('MODE', 'identity-preview');
      const fetch = fetcher(() => response({}));
      const controller = await flow();
      await expect(controller.beginMicrosoft()).rejects.toMatchObject({ code: 'unavailable' });
      expect(mocks.initialize).not.toHaveBeenCalled();
      expect(fetch).not.toHaveBeenCalled();
    },
  );

  it('allows only exact registered origins', async () => {
    const controller = await flow();
    for (const origin of ['https://clip-iisc.site', 'http://localhost:5173'])
      expect(controller.microsoftEnabled(origin)).toBe(true);
    for (const origin of [
      'http://127.0.0.1:5173',
      'https://clip-iisc.site.attacker.invalid',
      'http://localhost:5174',
      'http://clip-iisc.site',
    ])
      expect(controller.microsoftEnabled(origin)).toBe(false);
  });

  it('deduplicates concurrent starts without a second nonce request', async () => {
    let finish: (() => void) | undefined;
    mocks.redirect.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          finish = resolve;
        }),
    );
    const fetch = fetcher(() =>
      response({ nonce, expires_at: new Date(Date.now() + 600_000).toISOString() }),
    );
    const controller = await flow();
    const first = controller.beginMicrosoft();
    const second = controller.beginMicrosoft();
    expect(first).toBe(second);
    await vi.waitFor(() => expect(finish).toBeDefined());
    finish?.();
    await first;
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(mocks.redirect).toHaveBeenCalledTimes(1);
  });

  it('rejects malformed attempt metadata before redirecting', async () => {
    fetcher(() => response({ nonce: 'bad', expires_at: 'not-a-time' }));
    await expect((await flow()).beginMicrosoft()).rejects.toMatchObject({ code: 'unavailable' });
    expect(mocks.redirect).not.toHaveBeenCalled();
    expect(sessionStorage.length).toBe(0);
  });

  it('cleans a failed provider start without exposing diagnostics', async () => {
    fetcher(() => response({ nonce, expires_at: new Date(Date.now() + 600_000).toISOString() }));
    mocks.redirect.mockRejectedValue(new Error('PRIVATE_PROVIDER_FAILURE'));
    const controller = await flow();
    await expect(controller.beginMicrosoft()).rejects.not.toThrow('PRIVATE_PROVIDER_FAILURE');
    expect(sessionStorage.getItem(controller.MICROSOFT_ATTEMPT_KEY)).toBeNull();
    expect(mocks.clear).toHaveBeenCalledTimes(2);
  });

  it.each([
    ['sdk_initialization', 'initialize', 'database_unavailable'],
    ['sdk_cleanup', 'clear', 'database_not_open'],
    ['sdk_redirect', 'redirect', 'pkce_not_created'],
  ])('identifies a failed start at %s with only an allowlisted code', async (stage, method, code) => {
    fetcher(() => response({ nonce, expires_at: new Date(Date.now() + 600_000).toISOString() }));
    mocks[method as 'initialize' | 'clear' | 'redirect'].mockRejectedValueOnce(
      Object.assign(new Error('PRIVATE_PROVIDER_TOKEN_AND_URL'), { errorCode: code }),
    );
    const controller = await flow();
    const problem = await controller.beginMicrosoft().catch((error: Error) => error);
    expect(problem).toBeInstanceOf(controller.MicrosoftSignInError);
    expect((problem as Error).message).toContain(`start/${stage}/${code}`);
    expect((problem as Error).message).not.toContain('PRIVATE');
    expect(sessionStorage.getItem(controller.MICROSOFT_ATTEMPT_KEY)).toBeNull();
  });

  it('separates backend-attempt failure from SDK redirect failure', async () => {
    fetcher(() => response({}, 503));
    const problem = await (await flow()).beginMicrosoft().catch((error: Error) => error);
    expect((problem as Error).message).toContain('start/server_attempt');
    expect(mocks.redirect).not.toHaveBeenCalled();
  });

  it('identifies blocked browser storage without rendering its private message', async () => {
    fetcher(() => response({ nonce, expires_at: new Date(Date.now() + 600_000).toISOString() }));
    const write = vi.spyOn(Storage.prototype, 'setItem').mockImplementationOnce(() => {
      throw new DOMException('PRIVATE_STORAGE_VALUE', 'SecurityError');
    });
    try {
      const problem = await (await flow()).beginMicrosoft().catch((error: Error) => error);
      expect((problem as Error).message).toContain('start/local_marker/SecurityError');
      expect((problem as Error).message).not.toContain('PRIVATE');
      expect(mocks.redirect).not.toHaveBeenCalled();
    } finally {
      write.mockRestore();
    }
  });

  it('keeps start diagnostics generic in production builds', async () => {
    vi.stubEnv('DEV', false);
    mocks.initialize.mockRejectedValueOnce(
      Object.assign(new Error('PRIVATE_PROVIDER_FAILURE'), { errorCode: 'database_unavailable' }),
    );
    const problem = await (await flow()).beginMicrosoft().catch((error: Error) => error);
    expect((problem as Error).message).not.toContain('Development diagnostic');
    expect((problem as Error).message).not.toContain('database_unavailable');
    expect((problem as Error).message).not.toContain('PRIVATE');
  });

  it('exchanges one validated result, consumes marker, clears SDK and sanitizes URL', async () => {
    marker();
    window.history.replaceState(null, '', '/auth/callback?code=PRIVATE_URL#PRIVATE_FRAGMENT');
    const fetch = fetcher(() => response({ ...view, email: 'PRIVATE_EXTRA' }));
    const controller = await flow();
    const first = controller.completeMicrosoft();
    const second = controller.completeMicrosoft();
    expect(first).toBe(second);
    expect(await first).toEqual(view);
    expect(mocks.handle).toHaveBeenCalledTimes(1);
    expect(mocks.handle).toHaveBeenCalledWith({ navigateToLoginRequestUrl: false });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe('/api/auth/microsoft/sessions');
    expect(JSON.parse(String(fetch.mock.calls[0][1].body))).toEqual({ id_token: assertion });
    expect(mocks.clear).toHaveBeenCalledTimes(2);
    expect(sessionStorage.getItem(controller.MICROSOFT_ATTEMPT_KEY)).toBeNull();
    expect(location.pathname).toBe('/auth/callback');
    expect(location.search).toBe('');
    expect(location.hash).toBe('');
    await expect(controller.completeMicrosoft()).rejects.toMatchObject({ code: 'expired' });
    expect(fetch).toHaveBeenCalledTimes(1); // A settled result cannot revive UI after logout.
  });

  it.each(['missing', 'expired', 'malformed'])(
    'rejects a %s marker with no assertion exchange',
    async (mode) => {
      if (mode === 'expired') marker('2000-01-01T00:00:00.000000Z');
      if (mode === 'malformed') sessionStorage.setItem('clip.microsoft.redirect', '{bad');
      const fetch = fetcher(() => response(view));
      await expect((await flow()).completeMicrosoft()).rejects.toBeInstanceOf(Error);
      expect(fetch).not.toHaveBeenCalled();
      expect(mocks.handle).not.toHaveBeenCalled();
      expect(mocks.clear).toHaveBeenCalledTimes(1);
    },
  );

  it.each([
    { state: 'wrong' },
    { idTokenClaims: { nonce: 'wrong' } },
    { idToken: '' },
    { idToken: 'x'.repeat(16385) },
  ])('rejects mismatched/invalid SDK results without backend submission', async (change) => {
    marker();
    mocks.handle.mockResolvedValue(sdkResult(change));
    const fetch = fetcher(() => response(view));
    await expect((await flow()).completeMicrosoft()).rejects.toMatchObject({ code: 'failed' });
    expect(fetch).not.toHaveBeenCalled();
    expect(sessionStorage.length).toBe(0);
  });

  it('rechecks expiry after a slow provider response', async () => {
    let now = Date.now();
    vi.spyOn(Date, 'now').mockImplementation(() => now);
    marker(new Date(now + 1000).toISOString());
    mocks.handle.mockImplementation(async () => {
      now += 1001;
      return sdkResult();
    });
    const fetch = fetcher(() => response(view));
    await expect((await flow()).completeMicrosoft()).rejects.toMatchObject({ code: 'expired' });
    expect(fetch).not.toHaveBeenCalled();
  });

  it.each([
    [401, 'failed'],
    [429, 'limited'],
    [503, 'unavailable'],
  ] as const)('maps backend %s safely', async (status, code) => {
    marker();
    const fetch = fetcher(() => response({ error: { message: 'PRIVATE_BACKEND_DETAIL' } }, status));
    await expect((await flow()).completeMicrosoft()).rejects.toMatchObject({ code });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(sessionStorage.length).toBe(0);
  });

  it('never retries an uncertain exchange and clears SDK artifacts', async () => {
    marker();
    const fetch = fetcher(() => {
      throw new Error('PRIVATE_NETWORK_DETAIL');
    });
    await expect((await flow()).completeMicrosoft()).rejects.toMatchObject({ code: 'uncertain' });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(mocks.clear).toHaveBeenCalledTimes(2);
  });

  it('does not accept a temporary result from the Microsoft endpoint', async () => {
    marker();
    fetcher(() => response({ ...view, account_class: 'temporary' }));
    await expect((await flow()).completeMicrosoft()).rejects.toMatchObject({ code: 'uncertain' });
  });

  it('runs cleanup after provider errors and does not log their payloads', async () => {
    const log = vi.spyOn(console, 'log');
    const error = vi.spyOn(console, 'error');
    marker();
    mocks.handle.mockRejectedValue(new Error('PRIVATE_TOKEN_AND_PROVIDER_DATA'));
    fetcher(() => response(view));
    await expect((await flow()).completeMicrosoft()).rejects.not.toThrow(
      'PRIVATE_TOKEN_AND_PROVIDER_DATA',
    );
    expect(mocks.clear).toHaveBeenCalledTimes(1);
    expect(log).not.toHaveBeenCalled();
    expect(error).not.toHaveBeenCalled();
  });
});

describe('Microsoft callback UI', () => {
  it('handles StrictMode with one exchange and no displayed claims/assertions', async () => {
    marker();
    fetcher((path) => (path === '/api/me' ? response({}, 401) : response(view)));
    const { IdentityProvider } = await import('../src/features/identity');
    const { AuthCallbackPage } = await import('../src/pages/ScaffoldPages');
    render(
      <StrictMode>
        <MemoryRouter>
          <IdentityProvider>
            <AuthCallbackPage />
          </IdentityProvider>
        </MemoryRouter>
      </StrictMode>,
    );
    await screen.findByRole('heading', { name: 'You’re signed in' });
    expect(mocks.handle).toHaveBeenCalledTimes(1);
    expect(document.body.textContent).not.toContain(assertion);
    expect(document.body.textContent).not.toContain(nonce);
  });

  it('offers safe explicit session recovery without repeating the assertion exchange', async () => {
    marker();
    let checking = false;
    let posts = 0;
    fetcher((path) => {
      if (path === '/api/me') return checking ? response(view) : response({}, 401);
      posts++;
      throw new Error('PRIVATE_EXCHANGE_FAILURE');
    });
    const { IdentityProvider, MicrosoftCallback } = await import('../src/features/identity');
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <IdentityProvider>
          <MicrosoftCallback />
        </IdentityProvider>
      </MemoryRouter>,
    );
    expect((await screen.findByRole('alert')).textContent).toMatch(/Check your sign-in status/);
    checking = true;
    await user.click(screen.getByRole('button', { name: 'Check sign-in status' }));
    await screen.findByRole('heading', { name: 'You’re signed in' });
    expect(posts).toBe(1);
    expect(screen.getByText('Your current CLIP session is active.')).toBeTruthy();
  });

  it('renders the disabled preview button without starting a provider flow', async () => {
    vi.stubEnv('MODE', 'identity-preview');
    fetcher(() => response({}, 401));
    const { IdentityProvider, SignIn } = await import('../src/features/identity');
    render(
      <MemoryRouter>
        <IdentityProvider>
          <SignIn />
        </IdentityProvider>
      </MemoryRouter>,
    );
    expect(
      (await screen.findByRole('button', { name: 'Continue with Microsoft' })).hasAttribute(
        'disabled',
      ),
    ).toBe(true);
    expect(mocks.initialize).not.toHaveBeenCalled();
  });
});

describe('Microsoft recovery and cleanup failures', () => {
  it('allows a fresh explicit retry after SDK initialization recovers', async () => {
    mocks.initialize.mockRejectedValueOnce(new Error('PRIVATE_INIT_FAILURE'));
    const fetch = fetcher(() =>
      response({ nonce, expires_at: new Date(Date.now() + 600_000).toISOString() }),
    );
    const controller = await flow();
    await expect(controller.beginMicrosoft()).rejects.toMatchObject({ code: 'failed' });
    expect(fetch).not.toHaveBeenCalled();
    await controller.beginMicrosoft();
    expect(mocks.initialize).toHaveBeenCalledTimes(2);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('rejects a null SDK return and still clears its cache', async () => {
    marker();
    mocks.handle.mockResolvedValue(null);
    const fetch = fetcher(() => response(view));
    await expect((await flow()).completeMicrosoft()).rejects.toMatchObject({ code: 'failed' });
    expect(fetch).not.toHaveBeenCalled();
    expect(mocks.clear).toHaveBeenCalledTimes(1);
  });

  it('fails safely when SDK cleanup rejects, with no backend exchange', async () => {
    marker();
    mocks.clear.mockRejectedValue(new Error('PRIVATE_STORAGE_FAILURE'));
    const fetch = fetcher(() => response(view));
    await expect((await flow()).completeMicrosoft()).rejects.toMatchObject({ code: 'unavailable' });
    expect(fetch).not.toHaveBeenCalled();
    expect(sessionStorage.length).toBe(0);
  });

  it('does not replace the nonce attempt while a callback is in flight', async () => {
    marker();
    let finish: ((value: ReturnType<typeof sdkResult>) => void) | undefined;
    mocks.handle.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const fetch = fetcher(() => response(view));
    const controller = await flow();
    const completing = controller.completeMicrosoft();
    await vi.waitFor(() => expect(finish).toBeDefined());
    await expect(controller.beginMicrosoft()).rejects.toMatchObject({ code: 'failed' });
    finish?.(sdkResult());
    await completing;
    expect(fetch.mock.calls.map((row) => row[0])).toEqual(['/api/auth/microsoft/sessions']);
  });

  it('cannot revive a session when recovery completes after logout', async () => {
    marker();
    mocks.handle.mockRejectedValue(new Error('PRIVATE_PROVIDER_ERROR'));
    let waiting = false;
    let finish: ((value: Response) => void) | undefined;
    fetcher(() =>
      waiting
        ? new Promise<Response>((resolve) => {
            finish = resolve;
          })
        : response({}, 401),
    );
    const { IdentityProvider, MicrosoftCallback, useIdentity } = await import(
      '../src/features/identity'
    );
    function LogoutControl() {
      const identity = useIdentity();
      return (
        <button type="button" onClick={identity.clear}>
          Fixture logout
        </button>
      );
    }
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <IdentityProvider>
          <LogoutControl />
          <MicrosoftCallback />
        </IdentityProvider>
      </MemoryRouter>,
    );
    await screen.findByRole('alert');
    waiting = true;
    await user.click(screen.getByRole('button', { name: 'Check sign-in status' }));
    await vi.waitFor(() => expect(finish).toBeDefined());
    await user.click(screen.getByRole('button', { name: 'Fixture logout' }));
    finish?.(response(view));
    await screen.findByText('No current sign-in was confirmed. Return to sign in to start again.');
    expect(screen.queryByRole('heading', { name: 'You’re signed in' })).toBeNull();
  });
});

describe('Microsoft session deadline', () => {
  it('does not report a session whose deadline elapsed before the response arrived', async () => {
    marker();
    fetcher(() => response({ ...view, valid_until: '2000-01-01T00:00:00.000000Z' }));
    await expect((await flow()).completeMicrosoft()).rejects.toMatchObject({ code: 'failed' });
    expect(sessionStorage.length).toBe(0);
  });
});

describe('Development callback diagnostics', () => {
  it('shows only a fixed stage and an allowlisted SDK code', async () => {
    vi.stubEnv('DEV', true);
    marker();
    mocks.handle.mockRejectedValue(Object.assign(new Error('PRIVATE_PROVIDER_DETAIL'), {
      errorCode: 'post_request_failed',
    }));
    const controller = await flow();
    await expect(controller.completeMicrosoft()).rejects.toMatchObject({
      message: expect.stringContaining('Development diagnostic: sdk_return/post_request_failed.'),
    });
    await expect(controller.completeMicrosoft()).rejects.not.toHaveProperty('message', expect.stringContaining('PRIVATE_PROVIDER_DETAIL'));
  });

  it('does not expose unknown error codes or provider text', async () => {
    vi.stubEnv('DEV', true);
    marker();
    mocks.handle.mockRejectedValue(Object.assign(new Error('PRIVATE_PROVIDER_DETAIL'), {
      errorCode: 'PRIVATE_CODE_OR_TOKEN',
    }));
    const controller = await flow();
    try {
      await controller.completeMicrosoft();
      throw new Error('Expected callback failure');
    } catch (error) {
      expect((error as Error).message).toContain('Development diagnostic: sdk_return.');
      expect((error as Error).message).not.toContain('PRIVATE');
    }
  });

  it('keeps development stages out of production errors', async () => {
    vi.stubEnv('DEV', false);
    marker();
    mocks.handle.mockRejectedValue(Object.assign(new Error('PRIVATE_PROVIDER_DETAIL'), {
      errorCode: 'post_request_failed',
    }));
    const controller = await flow();
    await expect(controller.completeMicrosoft()).rejects.toMatchObject({
      message: 'We could not complete Microsoft sign-in. Try again with an eligible IISc account.',
    });
  });
});


it('preserves the callback diagnostic if later cache cleanup also fails', async () => {
  vi.stubEnv('DEV', true);
  marker();
  mocks.handle.mockRejectedValue(Object.assign(new Error('PRIVATE_PROVIDER_DETAIL'), {
    errorCode: 'post_request_failed',
  }));
  mocks.clear.mockRejectedValue(new Error('PRIVATE_CLEANUP_DETAIL'));
  const controller = await flow();
  await expect(controller.completeMicrosoft()).rejects.toMatchObject({
    message: expect.stringContaining('Development diagnostic: sdk_return/post_request_failed.'),
  });
});


it.each([
  Object.assign(new Error('PRIVATE_PROVIDER_DETAIL'), { errorCode: 'invalid_request', errorNo: '9002326' }),
  Object.assign(new Error('AADSTS9002326: PRIVATE_PROVIDER_DETAIL'), { errorCode: 'invalid_request' }),
])('shows only the numeric Microsoft error identifier in development', async (error) => {
  vi.stubEnv('DEV', true);
  marker();
  mocks.handle.mockRejectedValue(error);
  const controller = await flow();
  try {
    await controller.completeMicrosoft();
    throw new Error('Expected callback failure');
  } catch (failure) {
    expect((failure as Error).message).toContain('sdk_return/invalid_request/AADSTS9002326');
    expect((failure as Error).message).not.toContain('PRIVATE_PROVIDER_DETAIL');
  }
});

it('permits the fixed isolated restore host only with Microsoft sign-in enabled', async () => {
  const controller = await flow();
  expect(controller.microsoftEnabled('https://restore.clip-iisc.site')).toBe(true);
  expect(controller.microsoftEnabled('https://other.clip-iisc.site')).toBe(false);
  vi.stubEnv('VITE_MICROSOFT_SIGN_IN_ENABLED', 'false');
  expect(controller.microsoftEnabled('https://restore.clip-iisc.site')).toBe(false);
});
