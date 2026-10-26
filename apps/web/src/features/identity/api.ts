import { sessionFetch, SessionFetchError } from '../../shared/http/sessionFetch';
import type {
  ActivateTemporaryRequestWritable,
  ChallengeAccepted,
  RegistrationChallengeRequest,
  PasswordResetChallengeRequest,
  ResetTemporaryPasswordRequestWritable,
  SessionView,
  OwnContacts,
  MicrosoftLoginAttempt,
  MicrosoftSessionRequest,
  ContactValueRequest,
  IdentitySetOwnContactData,
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
  if (Date.parse(row.valid_until) <= Date.now()) throw new IdentityError(401);
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
  try {
    const response = await sessionFetch(path, {
      method,
      ...(body !== undefined ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}),
    }, {
      prefix: import.meta.env.MODE === 'identity-preview' ? '' : '/api',
      publicAuthentication: !protectedWrite,
    });
    if (!response.ok) throw new IdentityError(response.status);
    return response.status === 204 ? undefined : await response.json();
  } catch (error) {
    if (error instanceof IdentityError) throw error;
    if (error instanceof SessionFetchError) throw new IdentityError(error.status, error.mutationDispatched);
    throw new IdentityError(503, method !== 'GET');
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

/** Path field names come from the generated HTTP operation, never arbitrary input. */
export type ContactKind = IdentitySetOwnContactData['path']['contact_kind'];

/** Return only the three approved own-contact fields; reject malformed dependencies. */
function ownContacts(result: unknown): OwnContacts {
  if (!result || typeof result !== 'object') throw new IdentityError(503);
  const row = result as Record<string, unknown>;
  for (const field of ['email', 'phone', 'upi_id']) {
    if (row[field] !== null && typeof row[field] !== 'string') throw new IdentityError(503);
  }
  return {
    email: row.email as string | null,
    phone: row.phone as string | null,
    upi_id: row.upi_id as string | null,
  };
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
  async microsoftAttempt(): Promise<MicrosoftLoginAttempt> {
    const result = await request('/auth/microsoft/login-attempts', 'POST');
    if (!result || typeof result !== 'object') throw new IdentityError(503);
    const row = result as Record<string, unknown>;
    if (
      typeof row.nonce !== 'string' ||
      !/^[A-Za-z0-9_-]{32,128}$/.test(row.nonce) ||
      typeof row.expires_at !== 'string' ||
      !Number.isFinite(Date.parse(row.expires_at))
    )
      throw new IdentityError(503);
    return { nonce: row.nonce, expires_at: row.expires_at };
  },
  async microsoftSession(body: MicrosoftSessionRequest): Promise<SessionView> {
    const result = session(await request('/auth/microsoft/sessions', 'POST', body));
    if (result.account_class !== 'regular') throw new IdentityError(503, true);
    return result;
  },
  async contacts(): Promise<OwnContacts> {
    return ownContacts(await request('/me/contacts'));
  },
  async setContact(kind: ContactKind, body: ContactValueRequest) {
    if (!['email', 'phone', 'upi_id'].includes(kind)) throw new IdentityError(422);
    await request(`/me/contacts/${kind}`, 'PUT', body, true);
  },
  async deleteContact(kind: ContactKind) {
    if (!['email', 'phone', 'upi_id'].includes(kind)) throw new IdentityError(422);
    await request(`/me/contacts/${kind}`, 'DELETE', undefined, true);
  },
  async logout() {
    await request('/auth/session', 'DELETE', undefined, true);
  },
};

/** Map arbitrary failures to code-owned messages, excluding exception payloads. */
export function safeError(error: unknown): string {
  return error instanceof IdentityError ? error.message : new IdentityError(503).message;
}
