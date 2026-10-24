// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  IdentityProvider,
  IdentitySessionControl,
  SignIn,
  useIdentity,
} from '../src/features/identity';
import { identityApi, IdentityError, safeError } from '../src/features/identity/api';
import viteConfig from '../vite.config';

const session = {
  user_id: '11111111-2222-4333-8444-555555555555',
  account_class: 'temporary',
  valid_until: '2100-01-01T00:00:00.000000Z',
  display_name: null,
};
const challenge = {
  challenge_id: 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee',
  expires_at: '2100-01-01T00:00:00.000000Z',
};
function response(value: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(value), {
    status,
  });
}
function mockApi(handler: (path: string, init: RequestInit) => Response | Promise<Response>) {
  const fetcher = vi.fn((path: string, init: RequestInit) => Promise.resolve(handler(path, init)));
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}
function view() {
  return render(
    <MemoryRouter>
      <IdentityProvider>
        <IdentitySessionControl />
        <SignIn />
      </IdentityProvider>
    </MemoryRouter>,
  );
}
async function ready() {
  await screen.findByRole('button', { name: 'Create temporary account' });
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Sign in' }).hasAttribute('disabled')).toBe(false),
  );
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe('Identity UI with controlled reviewed HTTP results', () => {
  it('registers with one challenge write, verifies, clears secrets and logs out with CSRF', async () => {
    const calls: { path: string; init: RequestInit }[] = [];
    mockApi((path, init) => {
      calls.push({ path, init });
      if (path === '/me') return response({}, 401);
      if (path === '/auth/csrf') return response({ csrf_token: 'synthetic-csrf-value' });
      if (path === '/auth/session') return response(null, 204);
      if (path === '/auth/temporary/accounts') return response(session, 201);
      return response(challenge, 202);
    });
    const user = userEvent.setup();
    view();
    await ready();
    await user.click(screen.getByRole('button', { name: 'Create temporary account' }));
    await user.type(screen.getByLabelText('Email address'), 'synthetic-ui@example.invalid');
    await user.click(screen.getByRole('button', { name: 'Send verification code' }));
    await screen.findByRole('button', { name: 'Verify and create account' });
    expect(screen.getByRole('button', { name: 'Resend in 60s' }).hasAttribute('disabled')).toBe(
      true,
    );
    expect(screen.getByRole('status').textContent).toMatch(/If this address is eligible/);
    await user.type(screen.getByLabelText('Verification code'), '123456');
    expect(screen.getByLabelText('Password').getAttribute('minlength')).toBe('8');
    await user.type(screen.getByLabelText('Password'), 'demoPass');
    await user.click(screen.getByRole('button', { name: 'Verify and create account' }));
    await screen.findByRole('heading', { name: 'You’re signed in' });
    expect(screen.queryByLabelText('Password')).toBeNull();
    expect(calls.filter((row) => row.path.endsWith('/registration-challenges'))).toHaveLength(1);
    const activation = calls.find((row) => row.path.endsWith('/accounts'));
    expect(JSON.parse(String(activation?.init.body))).toEqual({
      challenge_id: challenge.challenge_id,
      code: '123456',
      password: 'demoPass',
    });
    await user.click(screen.getByRole('button', { name: 'Sign out' }));
    await screen.findByRole('heading', { name: 'Welcome back' });
    expect(calls.find((row) => row.path === '/auth/session')?.init.headers).toEqual({
      'X-CLIP-Request': '1',
      'X-CSRF-Token': 'synthetic-csrf-value',
    });
    expect(screen.getByLabelText('Password').getAttribute('value')).toBe('');
  });

  it('retains operation ID after uncertain challenge outcome without automatic resend', async () => {
    const operations: string[] = [];
    mockApi((path, init) => {
      if (path === '/me') return response({}, 401);
      operations.push(JSON.parse(String(init.body)).operation_id);
      if (operations.length === 1) throw new Error('PRIVATE_TRANSPORT_DETAIL');
      return response(challenge, 202);
    });
    const user = userEvent.setup();
    view();
    await ready();
    await user.click(screen.getByRole('button', { name: 'Create temporary account' }));
    await user.type(screen.getByLabelText('Email address'), 'synthetic-retry@example.invalid');
    await user.click(screen.getByRole('button', { name: 'Send verification code' }));
    expect((await screen.findByRole('alert')).textContent).toMatch(/could not confirm/);
    expect(operations).toHaveLength(1);
    expect(document.body.textContent).not.toContain('PRIVATE_TRANSPORT_DETAIL');
    await user.click(screen.getByRole('button', { name: 'Send verification code' }));
    await screen.findByRole('button', { name: 'Verify and create account' });
    expect(operations[0]).toBe(operations[1]);
  });

  it.each([401, 422, 429, 503])(
    'shows safe %s failure without echoing dependency input',
    async (status) => {
      mockApi((path) =>
        response({ private: 'PRIVATE_DEPENDENCY_PAYLOAD' }, path === '/me' ? 401 : status),
      );
      const user = userEvent.setup();
      view();
      await ready();
      await user.type(screen.getByLabelText('Email address'), 'synthetic-denied@example.invalid');
      await user.type(screen.getByLabelText('Password'), 'synthetic wrong password');
      await user.click(screen.getByRole('button', { name: 'Sign in' }));
      expect((await screen.findByRole('alert')).textContent?.length).toBeGreaterThan(0);
      expect(document.body.textContent).not.toContain('PRIVATE_DEPENDENCY_PAYLOAD');
      expect(screen.queryByRole('heading', { name: 'You’re signed in' })).toBeNull();
    },
  );

  it('ignores duplicate form submissions while credential exchange is pending', async () => {
    let complete: ((value: Response) => void) | undefined;
    const fetcher = mockApi((path) =>
      path === '/me'
        ? response({}, 401)
        : new Promise<Response>((resolve) => {
            complete = resolve;
          }),
    );
    const user = userEvent.setup();
    view();
    await ready();
    await user.type(screen.getByLabelText('Email address'), 'synthetic-pending@example.invalid');
    await user.type(screen.getByLabelText('Password'), 'synthetic passphrase');
    const form = screen.getByRole('form', { name: 'Temporary account' });
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(fetcher.mock.calls.filter((row) => row[0].endsWith('/sessions'))).toHaveLength(1);
    await act(async () => {
      complete?.(response(session));
    });
    await screen.findByRole('heading', { name: 'You’re signed in' });
  });

  it('rejects expired session results and clears UI on a visibility recheck', async () => {
    let current = session;
    mockApi(() => response(current));
    view();
    await screen.findByRole('heading', { name: 'You’re signed in' });
    current = { ...session, valid_until: '2000-01-01T00:00:00.000000Z' };
    fireEvent.focus(window);
    await screen.findByRole('heading', { name: 'Welcome back' });
  });

  it('fences an old session read after an explicit login result', async () => {
    let finish: ((value: Response) => void) | undefined;
    mockApi(
      () =>
        new Promise<Response>((resolve) => {
          finish = resolve;
        }),
    );
    function Probe() {
      const state = useIdentity();
      return (
        <button
          type="button"
          onClick={() => state.accept(session as Parameters<typeof state.accept>[0])}
        >
          {state.status}
        </button>
      );
    }
    render(
      <IdentityProvider>
        <Probe />
      </IdentityProvider>,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByRole('button').textContent).toBe('ready');
    await act(async () => {
      finish?.(response({}, 401));
    });
    expect(screen.getByRole('button').textContent).toBe('ready');
  });
});

describe('Cookie API and preview isolation', () => {
  it('uses same-origin cookies/no-store and strips extra response fields', async () => {
    const fetcher = mockApi(() =>
      response({
        ...session,
        email: 'PRIVATE_CONTACT',
        token: 'PRIVATE_TOKEN',
      }),
    );
    expect(await identityApi.me()).toEqual(session);
    expect(fetcher.mock.calls[0][1]).toMatchObject({
      credentials: 'same-origin',
      cache: 'no-store',
      method: 'GET',
    });
  });
  it.each([
    { ...session, user_id: 'not-a-uuid' },
    { ...session, account_class: 'admin' },
    { ...session, valid_until: 'bad-date' },
  ])('rejects malformed session dependency data', async (value) => {
    mockApi(() => response(value));
    await expect(identityApi.me()).rejects.toMatchObject({ status: 503 });
  });
  it('does not attempt protected writes without a valid CSRF response', async () => {
    const fetcher = mockApi(() => response({ csrf_token: 123 }));
    await expect(identityApi.logout()).rejects.toMatchObject({ status: 503 });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('redacts arbitrary failures', () => {
    expect(safeError(new Error('PRIVATE_PAYLOAD'))).not.toContain('PRIVATE_PAYLOAD');
    expect(safeError(new IdentityError(401))).toContain('session');
  });
  it('disables the preview proxy normally and refuses any preview build', () => {
    expect(() => viteConfig({ command: 'build', mode: 'identity-preview' })).toThrow(
      /cannot be built/,
    );
    const normal = viteConfig({ command: 'serve', mode: 'development' });
    expect(normal).toMatchObject({
      server: { host: '127.0.0.1', strictPort: true },
    });
    expect(normal.server?.proxy).toBeUndefined();
  });
});

describe('Temporary password recovery', () => {
  async function resetForm() {
    const user = userEvent.setup();
    view();
    await ready();
    await user.click(screen.getByRole('button', { name: 'Forgot password' }));
    await user.type(screen.getByLabelText('Email address'), 'synthetic-reset@example.invalid');
    await user.click(screen.getByRole('button', { name: 'Send reset code' }));
    await screen.findByRole('button', { name: 'Reset password' });
    return user;
  }

  it('uses reset-specific endpoints, clears secrets and requires a new sign-in', async () => {
    const calls: { path: string; body: unknown }[] = [];
    mockApi((path, init) => {
      calls.push({ path, body: init.body ? JSON.parse(String(init.body)) : undefined });
      if (path === '/me') return response({}, 401);
      if (path === '/auth/temporary/password-reset-challenges') return response(challenge, 202);
      if (path === '/auth/temporary/password-resets') return response(null, 204);
      return response(session);
    });
    const user = await resetForm();
    expect(screen.getByRole('status').textContent).toMatch(/If this address is eligible/);
    expect(screen.getByLabelText('New password').getAttribute('minlength')).toBe('8');
    await user.type(screen.getByLabelText('Verification code'), '654321');
    await user.type(screen.getByLabelText('New password'), 'resetPwd');
    await user.click(screen.getByRole('button', { name: 'Reset password' }));
    await screen.findByRole('heading', { name: 'Welcome back' });
    expect(screen.getByRole('status').textContent).toMatch(/Sign in with your new password/);
    expect(screen.getByLabelText('Password').getAttribute('value')).toBe('');
    expect(screen.queryByLabelText('Verification code')).toBeNull();
    expect(screen.queryByRole('heading', { name: 'You’re signed in' })).toBeNull();
    expect(calls.filter((row) => row.path.endsWith('/sessions'))).toHaveLength(0);
    expect(calls.filter((row) => row.path.endsWith('/registration-challenges'))).toHaveLength(0);
    expect(calls.find((row) => row.path.endsWith('/password-resets'))?.body).toEqual({
      challenge_id: challenge.challenge_id,
      code: '654321',
      new_password: 'resetPwd',
    });
    await user.type(screen.getByLabelText('Email address'), 'synthetic-reset@example.invalid');
    await user.type(screen.getByLabelText('Password'), 'resetPwd');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    await screen.findByRole('heading', { name: 'You’re signed in' });
  });

  it('does not resubmit an uncertain reset and guides login with the new password', async () => {
    let attempts = 0;
    mockApi((path) => {
      if (path === '/me') return response({}, 401);
      if (path.endsWith('/password-reset-challenges')) return response(challenge, 202);
      attempts++;
      throw new Error('PRIVATE_RESET_DEPENDENCY');
    });
    const user = await resetForm();
    await user.type(screen.getByLabelText('Verification code'), '654321');
    await user.type(screen.getByLabelText('New password'), 'resetPwd');
    await user.click(screen.getByRole('button', { name: 'Reset password' }));
    const error = await screen.findByRole('alert');
    expect(error.textContent).toMatch(/Try signing in with your new password/);
    expect(document.body.textContent).not.toContain('PRIVATE_RESET_DEPENDENCY');
    expect(attempts).toBe(1);
    await user.click(screen.getByRole('button', { name: 'Back to sign in' }));
    expect(screen.getByLabelText('Password').getAttribute('value')).toBe('');
  });

  it.each([422, 429, 503])('retains a safe reset screen after status %s', async (status) => {
    mockApi((path) =>
      path === '/me'
        ? response({}, 401)
        : path.endsWith('/password-reset-challenges')
          ? response(challenge, 202)
          : response({ private: 'PRIVATE_RESET_BODY' }, status),
    );
    const user = await resetForm();
    await user.type(screen.getByLabelText('Verification code'), '654321');
    await user.type(screen.getByLabelText('New password'), 'resetPwd');
    await user.click(screen.getByRole('button', { name: 'Reset password' }));
    await screen.findByRole('alert');
    expect(screen.getByRole('heading', { name: 'Choose a new password' })).toBeTruthy();
    expect(document.body.textContent).not.toContain('PRIVATE_RESET_BODY');
    expect(screen.queryByRole('heading', { name: 'You’re signed in' })).toBeNull();
  });

  it('blocks an expired challenge without submitting a reset', async () => {
    const fetcher = mockApi((path) =>
      path === '/me'
        ? response({}, 401)
        : response({ ...challenge, expires_at: '2000-01-01T00:00:00.000000Z' }, 202),
    );
    const user = await resetForm();
    await user.type(screen.getByLabelText('Verification code'), '654321');
    await user.type(screen.getByLabelText('New password'), 'resetPwd');
    await user.click(screen.getByRole('button', { name: 'Reset password' }));
    expect((await screen.findByRole('alert')).textContent).toMatch(/code has expired/);
    expect(fetcher.mock.calls.filter((row) => row[0].endsWith('/password-resets'))).toHaveLength(0);
  });

  it('counts Unicode password code points without truncating astral characters', async () => {
    const requests: unknown[] = [];
    mockApi((path, init) => {
      if (path === '/me') return response({}, 401);
      if (path.endsWith('/password-reset-challenges')) return response(challenge, 202);
      requests.push(JSON.parse(String(init.body)));
      return response(null, 204);
    });
    const user = await resetForm();
    await user.type(screen.getByLabelText('Verification code'), '654321');
    fireEvent.change(screen.getByLabelText('New password'), { target: { value: '🔒'.repeat(7) } });
    fireEvent.submit(screen.getByRole('form', { name: 'Reset temporary password' }));
    expect((await screen.findByRole('alert')).textContent).toMatch(/8–128 characters/);
    expect(requests).toHaveLength(0);
    fireEvent.change(screen.getByLabelText('New password'), { target: { value: '🔒'.repeat(8) } });
    fireEvent.submit(screen.getByRole('form', { name: 'Reset temporary password' }));
    await screen.findByRole('heading', { name: 'Welcome back' });
    expect(requests).toEqual([
      { challenge_id: challenge.challenge_id, code: '654321', new_password: '🔒'.repeat(8) },
    ]);
  });

  it('changing reset email stays in recovery and clears prior code/password', async () => {
    mockApi((path) => (path === '/me' ? response({}, 401) : response(challenge, 202)));
    const user = await resetForm();
    await user.type(screen.getByLabelText('Verification code'), '654321');
    await user.type(screen.getByLabelText('New password'), 'resetPwd');
    await user.click(screen.getByRole('button', { name: 'Use another email' }));
    expect(screen.getByRole('heading', { name: 'Forgot your password?' })).toBeTruthy();
    expect(screen.queryByLabelText('New password')).toBeNull();
    expect(screen.queryByLabelText('Verification code')).toBeNull();
  });
});
