import type { PublicClientApplication } from '@azure/msal-browser';
import type { SessionView } from '../../../../../contracts/generated/types.gen';
import { identityApi, IdentityError } from './api';

// Public registration values reviewed in docs/environment/identity-provider-setup.md.
export const MICROSOFT_CLIENT_ID = 'ab3a63e3-d4db-4c3c-b4bf-ac5f7573ffbb';
export const MICROSOFT_ATTEMPT_KEY = 'clip.microsoft.redirect';
const origins = new Set(['http://localhost:5173', 'https://clip-iisc.site']);
const messages = {
  unavailable: 'Microsoft sign-in is unavailable right now. Please try again later.',
  failed: 'We could not complete Microsoft sign-in. Try again with an eligible IISc account.',
  expired: 'This Microsoft sign-in attempt has expired. Start again from sign in.',
  uncertain:
    'We could not confirm Microsoft sign-in. Check your sign-in status before starting again.',
  limited: 'Too many sign-in attempts. Please wait before trying again.',
};

/** Code-owned messages only; no provider exception, assertion, URL or claim data. */
export class MicrosoftSignInError extends Error {
  constructor(readonly code: keyof typeof messages) {
    super(messages[code]);
    this.name = 'MicrosoftSignInError';
  }
}

/** Explicit activation and exact registered origin. Preview never contacts Microsoft. */
export function microsoftEnabled(
  origin: string = typeof window !== 'undefined' ? window.location.origin : '',
): boolean {
  return (
    typeof window !== 'undefined' &&
    import.meta.env.VITE_MICROSOFT_SIGN_IN_ENABLED === 'true' &&
    import.meta.env.MODE !== 'identity-preview' &&
    origins.has(origin)
  );
}

let sdk: Promise<PublicClientApplication> | null = null;
let starting: Promise<void> | null = null;
let completion: Promise<SessionView> | null = null;

/** Lazily initialize the actual pinned SDK, with scoped session cache and no logging.
 * Redirect requires SDK sessionStorage; no localStorage or CLIP bearer cache.
 * OIDC defaults include offline_access; no Graph data scope or silent acquisition.
 * Live startup/consent/cache cleanup still require separate provider verification.
 */
function client(): Promise<PublicClientApplication> {
  if (!sdk)
    sdk = (async () => {
      const { PublicClientApplication, BrowserCacheLocation, LogLevel } = await import(
        '@azure/msal-browser'
      );
      const app = new PublicClientApplication({
        auth: {
          clientId: MICROSOFT_CLIENT_ID,
          authority: 'https://login.microsoftonline.com/common',
          redirectUri: `${window.location.origin}/auth/callback`,
        },
        cache: { cacheLocation: BrowserCacheLocation.SessionStorage, cacheRetentionDays: 0 },
        system: {
          allowPlatformBroker: false,
          serverTelemetryEnabled: false,
          loggerOptions: {
            logLevel: LogLevel.Error,
            piiLoggingEnabled: false,
            loggerCallback: () => {},
          },
        },
      });
      await app.initialize();
      return app;
    })().catch((error) => {
      sdk = null;
      throw error;
    });
  return sdk;
}

type RedirectMarker = { state: string; nonce: string; expiresAt: string };

/** Consume one bounded own marker before awaiting any provider response.
 * Only public nonce/state/expiry is stored here; never a code/assertion/password.
 */
function takeMarker(): RedirectMarker {
  const raw = window.sessionStorage.getItem(MICROSOFT_ATTEMPT_KEY);
  window.sessionStorage.removeItem(MICROSOFT_ATTEMPT_KEY);
  if (!raw || raw.length > 2048) throw new MicrosoftSignInError('expired');
  const value: unknown = JSON.parse(raw);
  if (!value || typeof value !== 'object') throw new MicrosoftSignInError('failed');
  const row = value as Record<string, unknown>;
  if (
    typeof row.state !== 'string' ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(row.state) ||
    typeof row.nonce !== 'string' ||
    !/^[A-Za-z0-9_-]{32,128}$/.test(row.nonce) ||
    typeof row.expiresAt !== 'string' ||
    !Number.isFinite(Date.parse(row.expiresAt))
  )
    throw new MicrosoftSignInError('failed');
  if (Date.parse(row.expiresAt) <= Date.now()) throw new MicrosoftSignInError('expired');
  return { state: row.state, nonce: row.nonce, expiresAt: row.expiresAt };
}

/** Remove provider response material from the address bar without redirecting elsewhere. */
function cleanReturnUrl() {
  if (window.location.pathname === '/auth/callback')
    window.history.replaceState(null, '', '/auth/callback');
}

/** Map SDK/network/backend failures without exposing raw exception text. */
function failure(error: unknown): MicrosoftSignInError {
  if (error instanceof MicrosoftSignInError) return error;
  if (error instanceof IdentityError)
    return new MicrosoftSignInError(
      error.uncertain
        ? 'uncertain'
        : error.status === 429
          ? 'limited'
          : error.status === 401
            ? 'failed'
            : 'unavailable',
    );
  return new MicrosoftSignInError('failed');
}

/** Start only on an explicit user action: server nonce/cookie, then real SDK PKCE/state.
 * Concurrent clicks share one attempt; failed starts are never automatically retried.
 */
export function beginMicrosoft(): Promise<void> {
  if (starting) return starting;
  if (completion) return Promise.reject(new MicrosoftSignInError('failed'));
  starting = (async () => {
    let app: PublicClientApplication | null = null;
    try {
      if (!microsoftEnabled()) throw new MicrosoftSignInError('unavailable');
      app = await client();
      await app.clearCache();
      const attempt = await identityApi.microsoftAttempt();
      if (Date.parse(attempt.expires_at) <= Date.now()) throw new MicrosoftSignInError('expired');
      const marker: RedirectMarker = {
        state: crypto.randomUUID(),
        nonce: attempt.nonce,
        expiresAt: attempt.expires_at,
      };
      window.sessionStorage.setItem(MICROSOFT_ATTEMPT_KEY, JSON.stringify(marker));
      await app.loginRedirect({
        scopes: ['openid', 'profile', 'email'],
        nonce: marker.nonce,
        state: marker.state,
        prompt: 'select_account',
      });
    } catch (error) {
      try {
        window.sessionStorage.removeItem(MICROSOFT_ATTEMPT_KEY);
        await app?.clearCache();
      } catch {
        /* No raw storage/provider diagnostics. */
      }
      throw failure(error);
    } finally {
      starting = null;
    }
  })();
  return starting;
}

/** Deduplicate in-flight StrictMode calls and consume each attempt once: SDK validation,
 * matching own state/nonce, then one server assertion exchange. Backend signature,
 * issuer/audience/domain/nonce/cookie/account checks grant the actual CLIP session.
 * SDK cache and own marker are cleaned on all initialized paths; no SSO logout.
 */
export function completeMicrosoft(): Promise<SessionView> {
  if (completion) return completion;
  if (starting) return Promise.reject(new MicrosoftSignInError('failed'));
  completion = (async () => {
    let app: PublicClientApplication | null = null;
    let outcome: SessionView | undefined;
    let problem: MicrosoftSignInError | undefined;
    try {
      if (!microsoftEnabled()) throw new MicrosoftSignInError('unavailable');
      if (window.location.pathname !== '/auth/callback') throw new MicrosoftSignInError('failed');
      app = await client();
      const marker = takeMarker();
      const result = await app.handleRedirectPromise({ navigateToLoginRequestUrl: false });
      const claims = result?.idTokenClaims as Record<string, unknown> | undefined;
      if (
        !result ||
        result.state !== marker.state ||
        claims?.nonce !== marker.nonce ||
        typeof result.idToken !== 'string' ||
        !result.idToken ||
        result.idToken.length > 16384
      )
        throw new MicrosoftSignInError('failed');
      if (Date.parse(marker.expiresAt) <= Date.now()) throw new MicrosoftSignInError('expired');
      // Discard SDK artifacts before the CLIP exchange; only this local variable
      // carries the assertion to the canonical request. No application token cache.
      await app.clearCache();
      outcome = await identityApi.microsoftSession({ id_token: result.idToken });
    } catch (error) {
      problem = failure(error);
    } finally {
      try {
        window.sessionStorage.removeItem(MICROSOFT_ATTEMPT_KEY);
        await app?.clearCache();
      } catch {
        problem = new MicrosoftSignInError('unavailable');
      }
      try {
        cleanReturnUrl();
      } catch {
        problem = new MicrosoftSignInError('unavailable');
      }
    }
    if (problem) throw problem;
    if (!outcome) throw new MicrosoftSignInError('failed');
    return outcome;
  })();
  const current = completion;
  // Cache only in-flight work for StrictMode, never a settled login result that
  // could later revive stale UI after logout. Consumed markers reject replay.
  void current.then(
    () => {
      if (completion === current) completion = null;
    },
    () => {
      if (completion === current) completion = null;
    },
  );
  return current;
}
