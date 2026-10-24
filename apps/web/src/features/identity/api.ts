import type {
  ActivateTemporaryRequestWritable,
  ChallengeAccepted,
  RegistrationChallengeRequest,
  PasswordResetChallengeRequest,
  ResetTemporaryPasswordRequestWritable,
  SessionView,
  TemporarySessionRequestWritable,
} from '../../../../../contracts/generated/types.gen';

/** Reviewed safe status only; raw response/provider/input text is never surfaced. */
export class IdentityError extends Error {
  constructor(
    readonly status: number,
    readonly uncertain = false,
  ) {
    super(
      status === 401
        ? 'Sign-in failed or your session has ended.'
        : status === 403
          ? 'This action is not allowed. Refresh and try again.'
          : status === 422
            ? 'Check your details or request a new verification code.'
            : status === 429
              ? 'Too many attempts. Please wait before trying again.'
              : uncertain
                ? 'We could not confirm the result. Do not repeat the action automatically.'
                : 'We could not reach the service. Please try again later.',
    );
    this.name = 'IdentityError';
  }
}

/** Read only approved session fields; reject malformed/expired dependency data. */
function session(value: unknown): SessionView {
  if (!value || typeof value !== 'object') throw new IdentityError(503);
  const row = value as Record<string, unknown>;
  if (
    typeof row.user_id !== 'string' ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(row.user_id) ||
    !['regular', 'temporary'].includes(String(row.account_class)) ||
    typeof row.valid_until !== 'string' ||
    !Number.isFinite(Date.parse(row.valid_until)) ||
    (row.display_name != null && typeof row.display_name !== 'string')
  )
    throw new IdentityError(503);
  return {
    user_id: row.user_id,
    account_class: row.account_class as SessionView['account_class'],
    valid_until: row.valid_until,
    display_name: row.display_name as string | null | undefined,
  };
}

/** Same-origin, bounded cookie requests. Never retry credential/OTP writes. */
export async function request(
  path: string,
  method = 'GET',
  body?: unknown,
  protectedWrite = false,
): Promise<unknown> {
  const headers: Record<string, string> = {};
  if (method !== 'GET') {
    headers['X-CLIP-Request'] = '1';
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (protectedWrite) {
      const csrf = (await request('/auth/csrf')) as { csrf_token?: unknown };
      if (typeof csrf?.csrf_token !== 'string') throw new IdentityError(503);
      headers['X-CSRF-Token'] = csrf.csrf_token;
    }
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);
  try {
    const response = await fetch(path, {
      method,
      headers,
      credentials: 'same-origin',
      cache: 'no-store',
      signal: controller.signal,
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
    if (!response.ok) throw new IdentityError(response.status);
    return response.status === 204 ? undefined : await response.json();
  } catch (error) {
    if (error instanceof IdentityError) throw error;
    throw new IdentityError(503, method !== 'GET');
  } finally {
    clearTimeout(timeout);
  }
}

/** Validate a generic, non-enumerating challenge acknowledgement for either purpose. */
function acknowledgement(result: unknown): ChallengeAccepted {
  if (!result || typeof result !== 'object') throw new IdentityError(503, true);
  const row = result as Record<string, unknown>;
  if (
    typeof row.challenge_id !== 'string' ||
    typeof row.expires_at !== 'string' ||
    !Number.isFinite(Date.parse(row.expires_at))
  )
    throw new IdentityError(503, true);
  return { challenge_id: row.challenge_id, expires_at: row.expires_at };
}

/** Explicit reviewed endpoints; no target actor comes from browser input. */
export const identityApi = {
  async me() {
    return session(await request('/me'));
  },
  async login(body: TemporarySessionRequestWritable) {
    return session(await request('/auth/temporary/sessions', 'POST', body));
  },
  async register(body: RegistrationChallengeRequest): Promise<ChallengeAccepted> {
    const result = await request('/auth/temporary/registration-challenges', 'POST', body);
    return acknowledgement(result);
  },
  async resetChallenge(body: PasswordResetChallengeRequest): Promise<ChallengeAccepted> {
    return acknowledgement(
      await request('/auth/temporary/password-reset-challenges', 'POST', body),
    );
  },
  async resetPassword(body: ResetTemporaryPasswordRequestWritable) {
    await request('/auth/temporary/password-resets', 'POST', body);
  },
  async activate(body: ActivateTemporaryRequestWritable) {
    return session(await request('/auth/temporary/accounts', 'POST', body));
  },
  async logout() {
    await request('/auth/session', 'DELETE', undefined, true);
  },
};

/** Map arbitrary failures to code-owned messages, excluding exception payloads. */
export function safeError(error: unknown): string {
  return error instanceof IdentityError ? error.message : new IdentityError(503).message;
}
