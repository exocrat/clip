// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { IdentityProvider } from '../src/features/identity';
import { ConversationRuntime } from '../src/pages/ConversationRuntime';
import { ConversationDetailPage, ConversationsPage } from '../src/pages/ScaffoldPages';

vi.mock('../src/features/conversations/relay', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/features/conversations/relay')>();
  return {
    ...actual,
    openIndexedDbConversationSession: vi.fn(async () => ({
      stop: vi.fn(async () => undefined),
      crypto: { resumeParticipantSession: vi.fn(async () => true) },
      history: { read: vi.fn(async () => ({ received: [], sent: [] })) },
    })),
  };
});

function mount(path: string) {
  return render(<MemoryRouter initialEntries={[path]}>
    <IdentityProvider><ConversationRuntime><ConversationsPage /></ConversationRuntime></IdentityProvider>
  </MemoryRouter>);
}

function mountDetail(path: string) {
  return render(<MemoryRouter initialEntries={[path]}>
    <IdentityProvider><ConversationRuntime><Routes>
      <Route path="/my/conversations/:conversationId" element={<ConversationDetailPage />} />
    </Routes></ConversationRuntime></IdentityProvider>
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

  it('sends inbox filters and paging through the authenticated Conversations API', async () => {
    const paths: string[] = [];
    const conversation = {
      caller_role: 'initiator',
      conversation_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      counterparty_user_id: '22222222-2222-4222-8222-222222222222',
      current_offer: { amount_paise: 500000, offer_id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', revision: 1,
        status: 'submitted', updated_at: '2026-10-27T00:00:00Z' },
      initiator_user_id: '11111111-1111-4111-8111-111111111111',
      last_activity_at: '2026-10-27T00:00:00Z',
      origin_id: '33333333-3333-4333-8333-333333333333',
      origin_kind: 'sale_listing',
      own_last_read_sequence: 0,
      unread_count: 1,
    };
    const transport = vi.fn(async (path: RequestInfo | URL) => {
      const requestPath = String(path);
      if (requestPath === '/api/me') {
        return new Response(JSON.stringify({ user_id: '11111111-1111-4111-8111-111111111111',
          account_class: 'regular', valid_until: '2099-01-01T00:00:00Z' }),
        { headers: { 'Content-Type': 'application/json' } });
      }
      if (requestPath.startsWith('/api/conversations?')) {
        paths.push(requestPath);
        const url = new URL(requestPath, 'http://local.test');
        const page = Number(url.searchParams.get('page') ?? 1);
        return new Response(JSON.stringify({ items: [conversation], page, page_size: 20,
          has_next: page === 1 }), { headers: { 'Content-Type': 'application/json' } });
      }
      return new Response('{}', { status: 404, headers: { 'Content-Type': 'application/json' } });
    });
    vi.stubGlobal('fetch', transport);
    mount('/my/conversations');
    await screen.findByRole('heading', { name: 'Sale listing · 33333333…3333' });
    await waitFor(() => expect(paths.length).toBeGreaterThan(0));

    fireEvent.change(screen.getByLabelText('Type'), { target: { value: 'sale_listing' } });
    await waitFor(() => expect(paths.some((path) => {
      const query = new URL(path, 'http://local.test').searchParams;
      return query.get('origin_kind') === 'sale_listing' && query.get('page') === '1';
    })).toBe(true));

    fireEvent.change(screen.getByLabelText('Listing or request ID'), {
      target: { value: '33333333-3333-4333-8333-333333333333' },
    });
    await waitFor(() => expect(paths.some((path) =>
      new URL(path, 'http://local.test').searchParams.get('origin_id') === '33333333-3333-4333-8333-333333333333',
    )).toBe(true));

    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    await waitFor(() => expect(paths.some((path) => {
      const query = new URL(path, 'http://local.test').searchParams;
      return query.get('origin_id') === '33333333-3333-4333-8333-333333333333' && query.get('page') === '2';
    })).toBe(true));

    fireEvent.change(screen.getByLabelText('Participation'), { target: { value: 'initiated' } });
    await waitFor(() => expect(paths.some((path) => {
      const query = new URL(path, 'http://local.test').searchParams;
      return query.get('view') === 'initiated' && query.get('page') === '1';
    })).toBe(true));
  });

  it('connects seller selection through the public Listings API with the exact thread and revision', async () => {
    const conversationId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
    const listingId = '33333333-3333-4333-8333-333333333333';
    const buyerId = '22222222-2222-4222-8222-222222222222';
    vi.stubGlobal('crypto', { randomUUID: () => '44444444-4444-4444-8444-444444444444' });
    const requests: Array<{ path: string; init?: RequestInit }> = [];
    const listing = {
      revision: 7, availability: 'available', available_from: '2026-01-01T00:00:00Z',
      available_until: null, selected_buyer_id: null, selected_conversation_id: null,
    };
    const transport = vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      const requestPath = String(path);
      requests.push({ path: requestPath, init });
      if (requestPath === '/api/me') {
        return new Response(JSON.stringify({ user_id: '11111111-1111-4111-8111-111111111111',
          account_class: 'regular', valid_until: '2099-01-01T00:00:00Z' }), { headers: { 'Content-Type': 'application/json' } });
      }
      if (requestPath === `/api/conversations/${conversationId}`) {
        return new Response(JSON.stringify({ caller_role: 'origin_owner', conversation_id: conversationId,
          counterparty_user_id: buyerId, current_offer: null, initiator_user_id: buyerId,
          last_activity_at: '2026-10-27T00:00:00Z', origin_id: listingId, origin_kind: 'sale_listing',
          own_last_read_sequence: 0, unread_count: 0 }), { headers: { 'Content-Type': 'application/json' } });
      }
      if (requestPath === '/api/me/listings?page=1') {
        return new Response(JSON.stringify({ items: [{ ...listing, listing_id: listingId }],
          page: 1, page_size: 20, has_next: false }), { headers: { 'Content-Type': 'application/json' } });
      }
      if (requestPath === '/api/auth/csrf') {
        return new Response(JSON.stringify({ csrf_token: 'c'.repeat(64) }), { headers: { 'Content-Type': 'application/json' } });
      }
      if (requestPath === `/api/listings/${listingId}/selection`) {
        return new Response(JSON.stringify({ ...listing, revision: 8, availability: 'unavailable', selected_buyer_id: buyerId,
          selected_conversation_id: conversationId }), { headers: { 'Content-Type': 'application/json' } });
      }
      return new Response('{}', { status: 404, headers: { 'Content-Type': 'application/json' } });
    });
    vi.stubGlobal('fetch', transport);

    mountDetail(`/my/conversations/${conversationId}`);
    fireEvent.click(await screen.findByRole('button', { name: 'Select this buyer' }));

    expect(await screen.findByText('This buyer is selected; the listing is unavailable.')).toBeTruthy();
    const selectionWrite = requests.find((request) => request.path === `/api/listings/${listingId}/selection`);
    expect(selectionWrite?.init?.method).toBe('PUT');
    expect(JSON.parse(String(selectionWrite?.init?.body))).toEqual({ buyer_id: buyerId,
      conversation_id: conversationId, expected_revision: 7,
      operation_id: '44444444-4444-4444-8444-444444444444' });
    expect(requests.some((request) => request.path === `/api/conversations/${conversationId}`)).toBe(true);
  });
});
