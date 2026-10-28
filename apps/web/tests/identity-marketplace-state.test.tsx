// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { IdentityProvider, useIdentity } from '../src/features/identity';
import { AppShell } from '../src/app/AppShell';
import { ListingEditPage, MyListingsPage, SavedListingsPage } from '../src/pages/ScaffoldPages';

const idA = '11111111-2222-4333-8444-555555555555';
const idB = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee';
const listingId = '20000000-0000-4000-8000-000000000001';
const stamp = '2026-10-25T13:00:00.000000Z';
const session = (user_id = idA, account_class: 'regular' | 'temporary' = 'regular', valid_until = '2100-01-01T00:00:00.000000Z') => ({ user_id, account_class, valid_until, display_name: null });
function response(value: unknown, status = 200) { return new Response(JSON.stringify(value), { status }); }
function listing(title: string) {
  return { listing_id: listingId, title, description: 'Synthetic fixture only', category_code: 'books', category_label: 'Books', condition_code: 'good', condition_label: 'Good', asking_price_paise: 0, original_price_paise: 12500, negotiable: false, pickup_area: null, available_from: stamp, available_until: null, availability: 'available', sensitive_purchase: false, image_ids: [] };
}
function Controls({ switchActor }: { switchActor: () => ReturnType<typeof session> }) {
  const { accept, clear, refresh } = useIdentity();
  return <div>
    <button type="button" onClick={() => accept(switchActor())}>Switch actor</button>
    <button type="button" onClick={clear}>End local session</button>
    <button type="button" onClick={() => { void refresh(); }}>Refresh session</button>
  </div>;
}
function setup(mode: 'sales' | 'wanted' | 'saved', initial = session()) {
  let current = initial;
  let failSession = false;
  let hold: ((response: Response) => void) | undefined;
  let delayed = false;
  const fetcher = vi.fn((path: string) => {
    if (path === '/api/me') return Promise.resolve(failSession ? response({}, 503) : response(current));
    if (path === '/api/catalogue') return Promise.resolve(response({ categories: [{ code: 'books', label: 'Books' }], conditions: [{ code: 'good', label: 'Good' }] }));
    const title = current.user_id === idA ? 'Synthetic private A' : 'Synthetic private B';
    const sale = listing(title);
    const wanted = { request_id: listingId, title, description: 'Synthetic request', category_code: 'books', category_label: 'Books', budget_paise: null, created_at: stamp, updated_at: stamp, state: 'open', revision: 1 };
    const items = path.includes('/saved-listings') ? [{ listing_id: listingId, saved_at: stamp, listing: sale, retired: false }]
      : path.includes('/wanted-requests') ? [wanted]
      : [{ ...sale, owner_id: current.user_id, proof_available: null, revision: 1, selected_buyer_id: null, selected_conversation_id: null, created_at: stamp, updated_at: stamp }];
    if (!path.startsWith('/api/me/')) throw new Error('Unexpected fixture request');
    if (delayed) { delayed = false; return new Promise<Response>((resolve) => { hold = resolve; }); }
    return Promise.resolve(response({ items, page: 1, page_size: 20, has_next: false }));
  });
  vi.stubGlobal('fetch', fetcher);
  const page = mode === 'saved' ? <SavedListingsPage /> : <MyListingsPage />;
  const view = () => render(<MemoryRouter><IdentityProvider><Controls switchActor={() => { current = session(idB); return current; }} />{page}</IdentityProvider></MemoryRouter>);
  return { fetcher, view, fail: () => { failSession = true; }, delay: () => { delayed = true; }, resolveLate: () => hold?.(response({ items: [{ listing_id: listingId, saved_at: stamp, listing: listing('Synthetic private late A'), retired: false }], page: 1, page_size: 20, has_next: false })) };
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe('Private marketplace state across Identity transitions', () => {
  it.each(['sales', 'wanted', 'saved'] as const)('removes prior %s content on logout and reloads only the next actor', async (mode) => {
    const state = setup(mode);
    state.view();
    if (mode === 'wanted') fireEvent.click(await screen.findByRole('button', { name: 'Wanted Requests' }));
    await screen.findByText('Synthetic private A');
    if (mode === 'sales') expect(screen.getByText('Original price (seller-provided, unverified): ₹125')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'End local session' }));
    expect(screen.queryByText('Synthetic private A')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Create wanted request' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Switch actor' }));
    await screen.findByText('Synthetic private B');
    expect(screen.queryByText('Synthetic private A')).toBeNull();
  });
  it('also resets private views on a direct regular-to-regular actor switch', async () => {
    const state = setup('saved'); state.view();
    await screen.findByText('Synthetic private A');
    fireEvent.click(screen.getByRole('button', { name: 'Switch actor' }));
    expect(screen.queryByText('Synthetic private A')).toBeNull();
    await screen.findByText('Synthetic private B');
  });
  it('does not remount stable same-actor content on session refresh', async () => {
    const state = setup('saved'); state.view();
    await screen.findByText('Synthetic private A');
    const before = state.fetcher.mock.calls.filter(([path]) => path.includes('/saved-listings')).length;
    fireEvent.click(screen.getByRole('button', { name: 'Refresh session' }));
    await waitFor(() => expect(state.fetcher.mock.calls.filter(([path]) => path === '/api/me')).toHaveLength(2));
    expect(screen.getByText('Synthetic private A')).toBeTruthy();
    expect(state.fetcher.mock.calls.filter(([path]) => path.includes('/saved-listings'))).toHaveLength(before);
  });
  it('hides previously loaded private content if session verification fails', async () => {
    const state = setup('saved'); state.view();
    await screen.findByText('Synthetic private A'); state.fail();
    fireEvent.click(screen.getByRole('button', { name: 'Refresh session' }));
    await screen.findByRole('alert');
    expect(screen.queryByText('Synthetic private A')).toBeNull();
  });
  it('ignores an old private response arriving after logout', async () => {
    const state = setup('saved'); state.delay(); state.view();
    await waitFor(() => expect(state.fetcher.mock.calls.some(([path]) => path.includes('/saved-listings'))).toBe(true));
    fireEvent.click(screen.getByRole('button', { name: 'End local session' }));
    await act(async () => { state.resolveLate(); });
    expect(screen.queryByText('Synthetic private late A')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Switch actor' }));
    await screen.findByText('Synthetic private B');
  });
  it('preserves a Wanted draft on same-actor refresh and discards it on actor switch', async () => {
    const state = setup('wanted'); state.view();
    fireEvent.click(await screen.findByRole('button', { name: 'Wanted Requests' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Create wanted request' }));
    const title = await screen.findByLabelText('Title');
    fireEvent.change(title, { target: { value: 'Synthetic private draft A' } });
    fireEvent.click(screen.getByRole('button', { name: 'Refresh session' }));
    await waitFor(() => expect(state.fetcher.mock.calls.filter(([path]) => path === '/api/me')).toHaveLength(2));
    expect(screen.getByLabelText('Title').getAttribute('value')).toBe('Synthetic private draft A');
    fireEvent.click(screen.getByRole('button', { name: 'Switch actor' }));
    expect(screen.queryByLabelText('Title')).toBeNull();
    await screen.findByText('Synthetic private B');
  });
  it('unmounts private content at session expiry', async () => {
    const state = setup('saved', session(idA, 'regular', new Date(Date.now() + 700).toISOString())); state.view();
    await screen.findByText('Synthetic private A');
    await screen.findByRole('link', { name: 'Sign in' }, { timeout: 2000 });
    expect(screen.queryByText('Synthetic private A')).toBeNull();
  });
  it('blocks temporary editing/navigation while keeping Wanted creation available', async () => {
    const state = setup('wanted', session(idA, 'temporary'));
    state.view();
    fireEvent.click(await screen.findByRole('button', { name: 'Wanted Requests' }));
    await screen.findByRole('button', { name: 'Create wanted request' });
    cleanup();
    render(<MemoryRouter><IdentityProvider><AppShell /><ListingEditPage /></IdentityProvider></MemoryRouter>);
    await screen.findByText(/Temporary accounts cannot manage sale listings/);
    expect(screen.queryByRole('link', { name: 'New listing' })).toBeNull();
    expect(screen.queryByRole('link', { name: 'Edit listing' })).toBeNull();
    expect(state.fetcher.mock.calls.some(([path]) => path.startsWith('/api/listings/'))).toBe(false);
  });
});
