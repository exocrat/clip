// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { IdentityProvider } from '../src/features/identity';
import { ConversationRuntime } from '../src/pages/ConversationRuntime';
import { ConversationsPage } from '../src/pages/ScaffoldPages';

function mount(path: string) {
  return render(<MemoryRouter initialEntries={[path]}>
    <IdentityProvider><ConversationRuntime><ConversationsPage /></ConversationRuntime></IdentityProvider>
  </MemoryRouter>);
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('shared conversation route composition', () => {
  it('keeps the explicitly requested synthetic loopback demo independent of sign-in', async () => {
    const transport = vi.fn(async (_path: RequestInfo | URL) => new Response('{}', { status: 401 }));
    vi.stubGlobal('fetch', transport);
    mount('/my/conversations?demo=conversations');
    expect(await screen.findByText('Development demo · synthetic data only')).toBeTruthy();
    expect(transport.mock.calls.length).toBeGreaterThan(0);
    // Only Identity checks session state; synthetic chats never hit a real API.
    for (const call of transport.mock.calls) expect(String(call[0])).not.toContain('/conversations');
  });

  it('does not load real private chats for an anonymous session', async () => {
    const transport = vi.fn(async (_path: RequestInfo | URL) => new Response('{}', { status: 401 }));
    vi.stubGlobal('fetch', transport);
    mount('/my/conversations');
    expect(await screen.findByText('to view the marketplace.', { exact: false })).toBeTruthy();
    expect(screen.queryByText('Development demo · synthetic data only')).toBeNull();
  });

  it('connects a real-session summary to the shared cookie transport, not demo data', async () => {
    const transport = vi.fn(async (path: RequestInfo | URL) => {
      const body = String(path) === '/api/me'
        ? { user_id: '11111111-1111-4111-8111-111111111111', account_class: 'regular', valid_until: '2099-01-01T00:00:00Z' }
        : { items: [], page: 1, page_size: 100, has_next: false };
      return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } });
    });
    vi.stubGlobal('fetch', transport);
    mount('/my/conversations');
    await waitFor(() => expect(transport.mock.calls.some(([path]) => String(path).startsWith('/api/conversations?'))).toBe(true));
    expect(screen.queryByText('Development demo · synthetic data only')).toBeNull();
  });
});
