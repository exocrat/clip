// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ConversationListingDoneDeal, type ListingAvailabilityPort } from '../src/features/conversations/ConversationListingDoneDeal';
import { ConversationInbox, type ConversationInboxItem } from '../src/features/conversations/ConversationInbox';
import type { ListingSelectionView } from '../src/features/conversations/ConversationListingSelection';

const listingId = '11111111-1111-4111-8111-111111111111';
const state = (overrides: Partial<ListingSelectionView> = {}): ListingSelectionView => ({
  revision: 7, availability: 'available', available_from: '2026-01-01T00:00:00Z',
  available_until: '2099-01-01T00:00:00Z', selected_buyer_id: 'buyer',
  selected_conversation_id: 'thread', ...overrides,
});
const mount = (availability: ListingAvailabilityPort) => render(
  <ConversationListingDoneDeal listingId={listingId} availability={availability} />,
);
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('seller done-deal availability', () => {
  it('preserves the current window and sends no selection change', async () => {
    vi.stubGlobal('crypto', { randomUUID: () => 'operation-one' });
    const markUnavailable = vi.fn(async () => ({ kind: 'done' as const,
      listing: state({ revision: 8, availability: 'unavailable' }) }));
    mount({ readOwnedListing: vi.fn(async () => state()), markUnavailable });
    fireEvent.click(await screen.findByRole('button', { name: 'Mark as done deal' }));
    await screen.findByText('Listing unavailable');
    expect(markUnavailable).toHaveBeenCalledWith(listingId, {
      expected_revision: 7, availability: 'unavailable', available_from: state().available_from,
      available_until: state().available_until, operation_id: 'operation-one',
    });
    expect(screen.getByText(/Existing conversations remain open/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Mark as done deal' })).toBeNull();
  });

  it('reloads reopened availability on focus without remounting the group', async () => {
    let unavailable = true;
    mount({ readOwnedListing: vi.fn(async () => state({ availability: unavailable ? 'unavailable' : 'available' })), markUnavailable: vi.fn() });
    await screen.findByText('Listing unavailable');
    unavailable = false;
    fireEvent(window, new Event('focus'));
    expect(await screen.findByRole('button', { name: 'Mark as done deal' })).toBeTruthy();
  });

  it('keeps the exact command after an uncertain commit', async () => {
    const markUnavailable = vi.fn().mockResolvedValueOnce({ kind: 'dependency' })
      .mockResolvedValueOnce({ kind: 'done', listing: state({ availability: 'unavailable' }) });
    mount({ readOwnedListing: vi.fn(async () => state()), markUnavailable });
    fireEvent.click(await screen.findByRole('button', { name: 'Mark as done deal' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Retry marking unavailable' }));
    await screen.findByText('Listing unavailable');
    expect(markUnavailable.mock.calls[1]).toEqual(markUnavailable.mock.calls[0]);
  });

  it('reloads a stale revision and uses a new operation only after another click', async () => {
    let reads = 0;
    let operation = 0;
    vi.stubGlobal('crypto', { randomUUID: () => `operation-${++operation}` });
    const markUnavailable = vi.fn().mockResolvedValueOnce({ kind: 'conflict' })
      .mockResolvedValueOnce({ kind: 'done', listing: state({ availability: 'unavailable' }) });
    mount({ readOwnedListing: vi.fn(async () => state({ revision: ++reads === 1 ? 7 : 9 })), markUnavailable });
    fireEvent.click(await screen.findByRole('button', { name: 'Mark as done deal' }));
    await screen.findByText(/listing changed/i);
    fireEvent.click(screen.getByRole('button', { name: 'Mark as done deal' }));
    await screen.findByText('Listing unavailable');
    expect(markUnavailable.mock.calls[1][1].expected_revision).toBe(9);
    expect(markUnavailable.mock.calls[1][1].operation_id).not.toBe(markUnavailable.mock.calls[0][1].operation_id);
  });

  it('does not offer a write for an already unavailable listing or failed owner read', async () => {
    const markUnavailable = vi.fn();
    const view = mount({ readOwnedListing: vi.fn(async () => state({ availability: 'unavailable' })), markUnavailable });
    await screen.findByText('Listing unavailable');
    expect(screen.queryByRole('button', { name: 'Mark as done deal' })).toBeNull();
    view.unmount();
    mount({ readOwnedListing: vi.fn(async () => { throw new Error('private diagnostic'); }), markUnavailable });
    await screen.findByRole('alert');
    expect(screen.queryByRole('button', { name: 'Mark as done deal' })).toBeNull();
    expect(screen.queryByText('private diagnostic')).toBeNull();
    expect(markUnavailable).not.toHaveBeenCalled();
  });

  it('renders one action per seller listing group and none for buyer or Wanted groups', () => {
    const item: ConversationInboxItem = { conversation_id: 'one', label: 'Test chat', role: 'seller',
      origin_kind: 'sale_listing', origin_id: listingId, unread_count: 0, last_activity_at: '2026-01-01T00:00:00Z' };
    const action = vi.fn((_originId: string) => <span>Seller action</span>);
    render(<MemoryRouter><ConversationInbox conversations={[item, { ...item, conversation_id: 'two' },
      { ...item, conversation_id: 'buyer', origin_id: 'other', role: 'buyer' },
      { ...item, conversation_id: 'request', origin_kind: 'wanted_request', role: 'request author' }]}
      onRefresh={vi.fn()} onOpen={vi.fn()} renderSellerListingAction={action} /></MemoryRouter>);
    expect(action.mock.calls.map(([value]) => value)).toContain(listingId);
    expect(screen.getAllByText('Seller action')).toHaveLength(1);
  });
});
