// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { ConversationEmailPreference } from '../src/features/identity/ConversationEmailPreference';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it('loads the own setting and saves a changed preference with CSRF', async () => {
  let enabled = true;
  const fetcher = vi.fn(async (path: string, init: RequestInit) => {
    if (path === '/api/auth/csrf') return new Response(JSON.stringify({ csrf_token: 'c'.repeat(64) }), { status: 200 });
    if (init.method === 'PUT') enabled = JSON.parse(String(init.body)).enabled;
    return new Response(JSON.stringify({ enabled }), { status: 200 });
  });
  vi.stubGlobal('fetch', fetcher);
  render(<ConversationEmailPreference onUnauthorized={() => undefined} />);
  const toggle = await screen.findByRole('checkbox', { name: 'Email me about conversations' }) as HTMLInputElement;
  expect(toggle.checked).toBe(true);
  await userEvent.click(toggle);
  expect(toggle.checked).toBe(false);
  expect(fetcher.mock.calls.some(([path, init]) => path === '/api/me/conversation-email-preference' && init.method === 'PUT')).toBe(true);
});
