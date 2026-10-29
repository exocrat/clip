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

  it('shows public origin details and pages recent conversations without obsolete filters', async () => {
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
      if (requestPath === '/api/listings/33333333-3333-4333-8333-333333333333') {
        return new Response(JSON.stringify({
          listing_id: '33333333-3333-4333-8333-333333333333', title: 'Inspection campus bicycle',
          description: 'A bicycle for campus.', asking_price_paise: 100000, original_price_paise: null,
          negotiable: false, availability: 'available', available_from: '2026-01-01T00:00:00Z',
          available_until: null, category_code: 'bicycles', category_label: 'Bicycles',
          condition_code: 'good', condition_label: 'Good', image_ids: [], pickup_area: null,
          proof_available: null, sensitive_purchase: false,
        }), { headers: { 'Content-Type': 'application/json' } });
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
    expect(await screen.findByText('Inspection campus bicycle')).toBeTruthy();
    await waitFor(() => expect(paths.length).toBeGreaterThan(0));
    expect(screen.queryByLabelText('Type')).toBeNull();
    expect(screen.queryByLabelText('Participation')).toBeNull();
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0);
    expect(screen.queryByText('33333333-3333-4333-8333-333333333333')).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    await waitFor(() => expect(paths.some((path) => {
      const query = new URL(path, 'http://local.test').searchParams;
      return query.get('sort') === 'last_activity_desc' && query.get('page') === '2';
    })).toBe(true));
  });

  it('marks a seller listing unavailable through public Listings transport and refreshes its owner state', async () => {
    const listingId = '33333333-3333-4333-8333-333333333333';
    const ownerId = '11111111-1111-4111-8111-111111111111';
    const buyerId = '22222222-2222-4222-8222-222222222222';
    const requests: Array<{ path: string; init?: RequestInit }> = [];
    let updated = false;
    const listing = { listing_id: listingId, revision: 7, availability: 'available',
      available_from: '2026-01-01T00:00:00Z', available_until: '2099-01-01T00:00:00Z',
      selected_buyer_id: buyerId, selected_conversation_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa' };
    vi.stubGlobal('fetch', vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      const url = String(path);
      requests.push({ path: url, init });
      let body: unknown = {};
      if (url === '/api/me') body = { user_id: ownerId, account_class: 'regular', valid_until: '2099-01-01T00:00:00Z' };
      else if (url.startsWith('/api/conversations?')) body = { items: [{ caller_role: 'origin_owner',
        conversation_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', counterparty_user_id: buyerId,
        current_offer: null, initiator_user_id: buyerId, last_activity_at: '2026-10-27T00:00:00Z',
        origin_id: listingId, origin_kind: 'sale_listing', own_last_read_sequence: 0, unread_count: 0 }],
        page: 1, page_size: 100, has_next: false };
      else if (url === '/api/me/listings?page=1') body = { items: [{ ...listing,
        availability: updated ? 'unavailable' : 'available', revision: updated ? 8 : 7 }],
        page: 1, page_size: 20, has_next: false };
      else if (url === '/api/auth/csrf') body = { csrf_token: 'c'.repeat(64) };
      else if (url === `/api/listings/${listingId}/availability`) { updated = true; body = {}; }
      return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } });
    }));
    mount('/my/conversations');
    fireEvent.click(await screen.findByRole('button', { name: 'Mark as done deal' }));
    await screen.findByText('Listing unavailable');
    const request = requests.find((entry) => entry.path === `/api/listings/${listingId}/availability`);
    expect(request?.init?.method).toBe('PUT');
    expect(JSON.parse(String(request?.init?.body))).toEqual({ availability: 'unavailable', expected_revision: 7,
      available_from: listing.available_from, available_until: listing.available_until, operation_id: expect.any(String) });
    expect(requests.filter((entry) => entry.path === '/api/me/listings?page=1')).toHaveLength(2);
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

    expect(await screen.findByText('This buyer is selected for your private tracking.')).toBeTruthy();
    const detailLayout = document.querySelector('.conversation-detail-layout');
    expect(detailLayout?.querySelector('.conversation-thread')).toBeTruthy();
    expect(detailLayout?.querySelector('.conversation-offers')).toBeTruthy();
    expect(detailLayout?.querySelector('.conversation-thread__origin-context')).toBeTruthy();
    const selectionWrite = requests.find((request) => request.path === `/api/listings/${listingId}/selection`);
    expect(selectionWrite?.init?.method).toBe('PUT');
    expect(JSON.parse(String(selectionWrite?.init?.body))).toEqual({ buyer_id: buyerId,
      conversation_id: conversationId, expected_revision: 7,
      operation_id: '44444444-4444-4444-8444-444444444444' });
    expect(requests.some((request) => request.path === `/api/conversations/${conversationId}`)).toBe(true);
  });
});
