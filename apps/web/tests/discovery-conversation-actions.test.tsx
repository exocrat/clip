// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import { IdentityProvider } from '../src/features/identity';
import { DiscoveryPage } from '../src/pages/ScaffoldPages';
import { WantedContactAction } from '../src/features/search';
import { withCsrf } from './helpers/csrf';

const listingId = '20000000-0000-4000-8000-000000000001';
const threadId = '30000000-0000-4000-8000-000000000002';
// Isolate catalogue/layout fetching; retain the real page's account decision,
// public conversation action, CSRF transport and authorized navigation.
vi.mock('../src/features/search', async (original) => ({
  ...await original<typeof import('../src/features/search')>(),
  SaleDiscovery: ({ createListingAction, renderListingActions }: {
    createListingAction?: ReactNode; renderListingActions?: (id: string) => ReactNode;
  }) => <section>{createListingAction}{renderListingActions?.(listingId)}</section>,
  SaveListingAction: () => null,
}));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it('does not let a temporary buyer contact a Wanted requester', () => {
  const fetch = vi.fn();
  vi.stubGlobal('fetch', fetch);
  render(<MemoryRouter><WantedContactAction requestId={listingId} compact session={{ data: {
    user_id: '11111111-2222-4333-8444-555555555555', account_class: 'temporary',
    valid_until: '2100-01-01T00:00:00Z',
  } }} /></MemoryRouter>);
  const contact = screen.getByRole('button', { name: 'Contact requester' });
  expect((contact as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(contact);
  expect(fetch).not.toHaveBeenCalled();
  expect(screen.getByText('A regular account is required to respond.')).toBeTruthy();
});

it.each(['regular', 'temporary'] as const)('lets an eligible %s buyer message directly from Discover', async (accountClass) => {
  const writes: RequestInit[] = [];
  const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
  vi.stubGlobal('fetch', withCsrf(async (path, init) => {
    if (path === '/api/me') return response({ user_id: '11111111-2222-4333-8444-555555555555', account_class: accountClass, valid_until: '2100-01-01T00:00:00Z' });
    if (path === `/api/listings/${listingId}/conversations` && init.method === 'POST') {
      writes.push(init); return response({ conversation_id: threadId, created: true }, 201);
    }
    throw Error('Unexpected fixture request');
  }));
  render(<MemoryRouter initialEntries={['/']}><IdentityProvider><Routes>
    <Route path="/" element={<DiscoveryPage />} />
    <Route path={`/my/conversations/${threadId}`} element={<p>Authorized conversation</p>} />
  </Routes></IdentityProvider></MemoryRouter>);
  const message = await screen.findByRole('button', { name: 'Message seller' });
  expect(!!screen.queryByRole('link', { name: 'New Listing' })).toBe(accountClass === 'regular');
  fireEvent.click(message);
  await screen.findByText('Authorized conversation');
  expect(writes).toHaveLength(1);
  expect(new Headers(writes[0].headers).get('X-CSRF-Token')).toBeTruthy();
  expect(Object.keys(JSON.parse(String(writes[0].body)))).toEqual(['operation_id']);
});
