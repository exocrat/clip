// @vitest-environment jsdom
import { act, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { identityApi, IdentityError } from '../src/features/identity/api';

const session = {
  user_id: '11111111-2222-4333-8444-555555555555', account_class: 'temporary',
  valid_until: '2100-01-01T00:00:00Z', display_name: null,
};
let options: Record<string, unknown>;
let remove = vi.fn<(id: string) => void>();
beforeEach(() => {
  HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) { this.open = true; });
  HTMLDialogElement.prototype.close = vi.fn();
  remove = vi.fn<(id: string) => void>();
  window.turnstile = { render: vi.fn((_element, value) => { options = value; return 'widget'; }), remove };
});
afterEach(() => { delete window.turnstile; vi.unstubAllGlobals(); vi.restoreAllMocks(); });
function reply(status: number, challenged = false) {
  return new Response(JSON.stringify(status === 200 ? session : { error: { code: 'rate_limited' } }), {
    status, headers: challenged ? { 'X-CLIP-Challenge-Site-Key': 'synthetic-site-key' } : {},
  });
}

it('ordinary sign-in neither renders nor contacts the challenge provider', async () => {
  const fetcher = vi.fn().mockResolvedValue(reply(200)); vi.stubGlobal('fetch', fetcher);
  expect((await identityApi.login({ email: 'synthetic@example.invalid', password: 'synthetic-password' })).user_id).toBe(session.user_id);
  expect(window.turnstile?.render).not.toHaveBeenCalled();
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it('only user-completed challenge permits one retry with the same credential body', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(reply(429, true)).mockResolvedValueOnce(reply(200));
  vi.stubGlobal('fetch', fetcher);
  const work = identityApi.login({ email: 'synthetic@example.invalid', password: 'synthetic-password' });
  await screen.findByRole('heading', { name: 'Complete a security check' });
  await waitFor(() => expect(window.turnstile?.render).toHaveBeenCalledTimes(1));
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(options.action).toBe('clip_signin');
  await act(async () => { (options.callback as (token: string) => void)('one-use-proof'); await work; });
  expect(fetcher).toHaveBeenCalledTimes(2);
  expect(new Headers(fetcher.mock.calls[1][1].headers).get('X-CLIP-Challenge-Token')).toBe('one-use-proof');
  expect(fetcher.mock.calls[1][1].body).toBe(fetcher.mock.calls[0][1].body);
  expect(remove).toHaveBeenCalledTimes(1);
});

it('cancellation sends no credential retry and cleans up the widget', async () => {
  const fetcher = vi.fn().mockResolvedValue(reply(429, true)); vi.stubGlobal('fetch', fetcher);
  const work = identityApi.login({ email: 'synthetic@example.invalid', password: 'synthetic-password' });
  const result = work.catch((error: unknown) => error);
  const button = await screen.findByRole('button', { name: 'Cancel' });
  await waitFor(() => expect(window.turnstile?.render).toHaveBeenCalled());
  await act(async () => { button.click(); await result; });
  expect(await result).toBeInstanceOf(IdentityError);
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(remove).toHaveBeenCalledTimes(1);
});

it.each([401, 503])('does not replay a failed or uncertain response (%s)', async (status) => {
  const fetcher = vi.fn().mockResolvedValue(reply(status, true)); vi.stubGlobal('fetch', fetcher);
  await expect(identityApi.login({ email: 'synthetic@example.invalid', password: 'synthetic-password' })).rejects.toBeInstanceOf(IdentityError);
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(window.turnstile?.render).not.toHaveBeenCalled();
});

it('a rejected challenged retry does not start an unlimited retry loop', async () => {
  const fetcher = vi.fn().mockResolvedValue(reply(429, true)); vi.stubGlobal('fetch', fetcher);
  const result = identityApi.login({ email: 'synthetic@example.invalid', password: 'synthetic-password' }).catch((error: unknown) => error);
  await screen.findByRole('heading', { name: 'Complete a security check' });
  await waitFor(() => expect(window.turnstile?.render).toHaveBeenCalled());
  await act(async () => { (options.callback as (token: string) => void)('rejected-proof'); await result; });
  expect(await result).toBeInstanceOf(IdentityError);
  expect(fetcher).toHaveBeenCalledTimes(2);
});

it('leaving the page cancels the pending challenge without replaying credentials', async () => {
  const fetcher = vi.fn().mockResolvedValue(reply(429, true)); vi.stubGlobal('fetch', fetcher);
  const result = identityApi.login({ email: 'synthetic@example.invalid', password: 'synthetic-password' }).catch((error: unknown) => error);
  await screen.findByRole('heading', { name: 'Complete a security check' });
  await waitFor(() => expect(window.turnstile?.render).toHaveBeenCalled());
  await act(async () => { window.dispatchEvent(new PopStateEvent('popstate')); await result; });
  expect(await result).toBeInstanceOf(IdentityError);
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(remove).toHaveBeenCalledTimes(1);
});

it.each(['expired-callback', 'error-callback', 'timeout-callback'])('provider %s does not replay credentials', async (callback) => {
  const fetcher = vi.fn().mockResolvedValue(reply(429, true)); vi.stubGlobal('fetch', fetcher);
  const result = identityApi.login({ email: 'synthetic@example.invalid', password: 'synthetic-password' }).catch((error: unknown) => error);
  await screen.findByRole('heading', { name: 'Complete a security check' });
  await waitFor(() => expect(window.turnstile?.render).toHaveBeenCalled());
  await act(async () => { (options[callback] as () => void)(); await result; });
  expect(await result).toBeInstanceOf(IdentityError);
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(remove).toHaveBeenCalledTimes(1);
});

it('a blocked provider script fails safely without retrying the rejected write', async () => {
  delete window.turnstile;
  const fetcher = vi.fn().mockResolvedValue(reply(429, true)); vi.stubGlobal('fetch', fetcher);
  const result = identityApi.login({ email: 'synthetic@example.invalid', password: 'synthetic-password' }).catch((error: unknown) => error);
  await screen.findByRole('heading', { name: 'Complete a security check' });
  await waitFor(() => expect(document.querySelector('script[src^="https://challenges.cloudflare.com/"]')).not.toBeNull());
  await act(async () => {
    document.querySelector('script[src^="https://challenges.cloudflare.com/"]')?.dispatchEvent(new Event('error'));
    await result;
  });
  expect(await result).toBeInstanceOf(IdentityError);
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(await result).toHaveProperty('message', 'The security check could not be completed. Please try again.');
  expect(document.querySelector('script[src^="https://challenges.cloudflare.com/"]')).toBeNull();
});


it.each(['register', 'resetChallenge'] as const)('recovers a confirmed-refused OTP %s request once using the same operation', async (method) => {
  const accepted = { challenge_id: '11111111-2222-4333-8444-555555555555', expires_at: '2100-01-01T00:00:00Z' };
  const fetcher = vi.fn().mockResolvedValueOnce(reply(429, true)).mockResolvedValueOnce(new Response(JSON.stringify(accepted), { status: 202 }));
  vi.stubGlobal('fetch', fetcher);
  const work = identityApi[method]({ email: 'synthetic@example.invalid', operation_id: crypto.randomUUID() });
  await screen.findByRole('heading', { name: 'Complete a security check' });
  await waitFor(() => expect(window.turnstile?.render).toHaveBeenCalled());
  await act(async () => { (options.callback as (token: string) => void)('one-use-otp-proof'); await work; });
  expect(await work).toEqual(accepted);
  expect(fetcher).toHaveBeenCalledTimes(2);
  expect(fetcher.mock.calls[1][1].body).toBe(fetcher.mock.calls[0][1].body);
  expect(new Headers(fetcher.mock.calls[1][1].headers).get('X-CLIP-Challenge-Token')).toBe('one-use-otp-proof');
});


it.each(['activate', 'resetPassword'] as const)('replays refused OTP completion %s only after explicit proof', async (method) => {
  const fetcher = vi.fn().mockResolvedValueOnce(reply(429, true)).mockResolvedValueOnce(method === 'activate' ? reply(200) : new Response(null, { status: 204 }));
  vi.stubGlobal('fetch', fetcher);
  const body = { challenge_id: '11111111-2222-4333-8444-555555555555', code: '123456', password: 'synthetic-password', new_password: 'synthetic-password' };
  const work = method === 'activate' ? identityApi.activate(body) : identityApi.resetPassword(body);
  await screen.findByRole('heading', { name: 'Complete a security check' });
  await waitFor(() => expect(window.turnstile?.render).toHaveBeenCalled());
  await act(async () => { (options.callback as (token: string) => void)('one-use-completion-proof'); await work; });
  await work;
  expect(fetcher).toHaveBeenCalledTimes(2);
  expect(fetcher.mock.calls[1][1].body).toBe(fetcher.mock.calls[0][1].body);
});
