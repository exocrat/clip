// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  ConversationListingSelection,
  isSellerSaleListingConversation,
  type ListingSelectionPort,
  type ListingSelectionView,
} from '../src/features/conversations/ConversationListingSelection';

const listingId = '11111111-1111-4111-8111-111111111111';
const conversationId = '22222222-2222-4222-8222-222222222222';
const buyerId = '33333333-3333-4333-8333-333333333333';

function state(overrides: Partial<ListingSelectionView> = {}): ListingSelectionView {
  return {
    revision: 7,
    availability: 'available',
    available_from: '2026-01-01T00:00:00Z',
    available_until: null,
    selected_buyer_id: null,
    selected_conversation_id: null,
    ...overrides,
  };
}

function renderSelection(selection: ListingSelectionPort) {
  render(<ConversationListingSelection listingId={listingId} conversationId={conversationId}
    buyerId={buyerId} selection={selection} />);
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('seller selection in a Sale Listing conversation', () => {
  it('limits the control to the verified Sale Listing owner role', () => {
    expect(isSellerSaleListingConversation({ caller_role: 'origin_owner', origin_kind: 'sale_listing' })).toBe(true);
    expect(isSellerSaleListingConversation({ caller_role: 'initiator', origin_kind: 'sale_listing' })).toBe(false);
    expect(isSellerSaleListingConversation({ caller_role: 'origin_owner', origin_kind: 'wanted_request' })).toBe(false);
  });

  it('allows selection without an offer and sends the exact current revision and conversation', async () => {
    vi.stubGlobal('crypto', { randomUUID: () => '44444444-4444-4444-8444-444444444444' });
    const selectBuyer = vi.fn(async () => ({
      kind: 'selected' as const,
      listing: state({ revision: 8, availability: 'unavailable', selected_buyer_id: buyerId,
        selected_conversation_id: conversationId }),
    }));
    renderSelection({ readOwnedListing: vi.fn(async () => state()), selectBuyer });

    fireEvent.click(await screen.findByRole('button', { name: 'Select this buyer' }));

    await screen.findByText('This buyer is selected; the listing is unavailable.');
    expect(selectBuyer).toHaveBeenCalledWith(listingId, {
      buyer_id: buyerId,
      conversation_id: conversationId,
      expected_revision: 7,
      operation_id: '44444444-4444-4444-8444-444444444444',
    });
    expect(screen.getByText(/marks the listing unavailable.*does not accept an offer/i)).toBeTruthy();
  });

  it('retries an uncertain outcome with the same command and operation ID', async () => {
    vi.stubGlobal('crypto', { randomUUID: () => '55555555-5555-4555-8555-555555555555' });
    const selectBuyer = vi.fn()
      .mockResolvedValueOnce({ kind: 'dependency' as const })
      .mockResolvedValueOnce({ kind: 'selected' as const,
        listing: state({ revision: 8, availability: 'unavailable', selected_buyer_id: buyerId, selected_conversation_id: conversationId }) });
    renderSelection({ readOwnedListing: vi.fn(async () => state()), selectBuyer });

    fireEvent.click(await screen.findByRole('button', { name: 'Select this buyer' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Retry selection' }));

    await screen.findByText('This buyer is selected; the listing is unavailable.');
    expect(selectBuyer).toHaveBeenCalledTimes(2);
    expect(selectBuyer.mock.calls[0]).toEqual(selectBuyer.mock.calls[1]);
  });

  it('refreshes after a revision conflict and uses the new revision for a new attempt', async () => {
    let reads = 0;
    const readOwnedListing = vi.fn(async () => state({ revision: ++reads === 1 ? 7 : 8 }));
    const selectBuyer = vi.fn()
      .mockResolvedValueOnce({ kind: 'conflict' as const })
      .mockResolvedValueOnce({ kind: 'selected' as const,
        listing: state({ revision: 9, availability: 'unavailable', selected_buyer_id: buyerId, selected_conversation_id: conversationId }) });
    let nextOperation = 0;
    vi.stubGlobal('crypto', { randomUUID: () => `66666666-6666-4666-8666-66666666666${++nextOperation}` });
    renderSelection({ readOwnedListing, selectBuyer });

    fireEvent.click(await screen.findByRole('button', { name: 'Select this buyer' }));
    await screen.findByText(/listing changed/i);
    fireEvent.click(screen.getByRole('button', { name: 'Select this buyer' }));

    await screen.findByText('This buyer is selected; the listing is unavailable.');
    expect(selectBuyer.mock.calls[0][1].expected_revision).toBe(7);
    expect(selectBuyer.mock.calls[1][1].expected_revision).toBe(8);
    expect(selectBuyer.mock.calls[0][1].operation_id).not.toBe(selectBuyer.mock.calls[1][1].operation_id);
  });

  it('does not offer selection when the listing is unavailable or outside its window', async () => {
    renderSelection({ readOwnedListing: vi.fn(async () => state({ availability: 'unavailable' })),
      selectBuyer: vi.fn() });

    await screen.findByText(/only while the listing is available/i);
    expect(screen.queryByRole('button', { name: /select this buyer/i })).toBeNull();
  });

  it('shows reopened availability accurately and lets the seller select the same buyer again', async () => {
    const selectBuyer = vi.fn(async () => ({ kind: 'selected' as const,
      listing: state({ revision: 8, availability: 'unavailable', selected_buyer_id: buyerId,
        selected_conversation_id: conversationId }) }));
    renderSelection({ readOwnedListing: vi.fn(async () => state({ selected_buyer_id: buyerId,
      selected_conversation_id: conversationId })), selectBuyer });

    await screen.findByText('This buyer is selected, but the listing is currently available.');
    fireEvent.click(screen.getByRole('button', { name: 'Select this buyer' }));
    await screen.findByText('This buyer is selected; the listing is unavailable.');
    expect(selectBuyer).toHaveBeenCalledTimes(1);
  });

  it('does not offer an action if the owner-only listing state cannot be loaded', async () => {
    renderSelection({ readOwnedListing: vi.fn(async () => { throw new Error('private diagnostic'); }),
      selectBuyer: vi.fn() });

    await screen.findByRole('alert');
    expect(screen.queryByRole('button', { name: 'Select this buyer' })).toBeNull();
    expect(screen.queryByText('private diagnostic')).toBeNull();
  });
});
