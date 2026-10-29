// @vitest-environment jsdom
import { act, cleanup, configure, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { IdentityProvider, useIdentity } from '../src/features/identity';
import { ListingDetailPage } from '../src/pages/ScaffoldPages';
import { withCsrf } from './helpers/csrf';

const listingId = '20000000-0000-4000-8000-000000000001';
const threadId = '30000000-0000-4000-8000-000000000002';
const response = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });
// Whole-suite parallel workers can delay jsdom setup beyond its 1s default.
configure({ asyncUtilTimeout: 5_000 });

function EndSession() {
  const { clear } = useIdentity();
  return <button type="button" onClick={clear}>End session</button>;
}

/** HTTP doubles isolate UI behavior; actual owner SQL/authorization is checked separately. */
function setup(post = vi.fn(async () => response({ conversation_id: threadId, created: true }, 201))) {
  const writes: RequestInit[] = [];
  vi.stubGlobal('fetch', withCsrf(async (path, init) => {
    if (path === '/api/me') return response({ user_id: '11111111-2222-4333-8444-555555555555', account_class: 'regular', valid_until: '2100-01-01T00:00:00Z' });
    if (path.endsWith('/conversations') && init.method === 'POST') { writes.push(init); return post(); }
    if (path.startsWith('/api/me/saved-listings')) return response({ items: [], page: 1, page_size: Number(new URL(path, 'http://localhost').searchParams.get('page_size')), has_next: false });
    if (path === `/api/listings/${listingId}`) return response({ listing_id: listingId, title: 'Synthetic listing', description: 'Fixture only', category_code: 'books', category_label: 'Books', condition_code: 'good', condition_label: 'Good', asking_price_paise: 100, original_price_paise: 25000, negotiable: false, pickup_area: null, available_from: '2026-01-01T00:00:00Z', available_until: null, availability: 'available', proof_available: null, sensitive_purchase: false, image_ids: [] });
    throw new Error('Unexpected fixture path');
  }));
  render(<MemoryRouter initialEntries={[`/listings/${listingId}`]}><IdentityProvider><EndSession /><Routes>
    <Route path="/listings/:listingId" element={<ListingDetailPage />} />
    <Route path={`/my/conversations/${threadId}`} element={<p>Authorized chat target</p>} />
  </Routes></IdentityProvider></MemoryRouter>);
  return { post, writes };
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe('Listing page conversation entry point', () => {
  it('opens the server-returned thread through the real page slot and shared CSRF transport', async () => {
    const state = setup();
    expect(await screen.findByText('Original price (Seller Provided): ₹250')).toBeTruthy();
    fireEvent.click(await screen.findByRole('button', { name: 'Message seller' }));
    await screen.findByText('Authorized chat target');
    expect(state.writes).toHaveLength(1);
    expect(Object.keys(JSON.parse(String(state.writes[0].body)))).toEqual(['operation_id']);
    expect(new Headers(state.writes[0].headers).get('X-CSRF-Token')).toBeTruthy();
  });

  it('keeps one intent on failure/retry and accepts a server-confirmed existing pair', async () => {
    const post = vi.fn(async () => response({ conversation_id: threadId, created: false }));
    post.mockResolvedValueOnce(response({ private: 'withheld' }, 503));
    const state = setup(post);
    const messageButton = await screen.findByRole('button', { name: 'Message seller' });
    const action = messageButton.parentElement;
    if (!action) throw new Error('Message action container missing');
    fireEvent.click(messageButton);
    await within(action).findByText('A required service is unavailable. Your form has been kept; try again later.');
    expect(screen.queryByText('Authorized chat target')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Message seller' }));
    await screen.findByText('Authorized chat target');
    expect(state.writes[1].body).toEqual(state.writes[0].body);
  });

  it('rejects an invalid returned target without navigating', async () => {
    setup(vi.fn(async () => response({ conversation_id: '../sign-in', created: true })));
    const messageButton = await screen.findByRole('button', { name: 'Message seller' });
    const action = messageButton.parentElement;
    if (!action) throw new Error('Message action container missing');
    fireEvent.click(messageButton);
    await within(action).findByRole('alert');
    expect(screen.queryByText('Authorized chat target')).toBeNull();
  }, 10_000);

  it('ignores a late successful result after the session boundary unmounts the action', async () => {
    let finish!: (value: Response) => void;
    setup(vi.fn(() => new Promise<Response>((resolve) => { finish = resolve; })));
    fireEvent.click(await screen.findByRole('button', { name: 'Message seller' }));
    await screen.findByRole('button', { name: 'Opening conversation…' });
    // Wait for the async fresh-CSRF preflight to dispatch the pending action.
    await act(async () => { await Promise.resolve(); });
    fireEvent.click(screen.getByRole('button', { name: 'End session' }));
    await act(async () => { finish(response({ conversation_id: threadId, created: true })); });
    expect(screen.queryByText('Authorized chat target')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Message seller' })).toBeNull();
  });
});
