// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ConversationInbox, type ConversationInboxFilters, type ConversationInboxItem } from '../src/features/conversations';

const filters: ConversationInboxFilters = { view: 'all', sort: 'last_activity_desc' };
const conversations: ConversationInboxItem[] = [
  { conversation_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', label: 'Sale listing conversation',
    role: 'seller', last_activity_at: '2026-10-27T00:00:00Z', unread_count: 0,
    origin_kind: 'sale_listing', origin_id: '11111111-1111-4111-8111-111111111111',
    counterparty_user_id: '22222222-2222-4222-8222-222222222222',
    group_unread_count: 3,
    current_offer: { amount_paise: 500000, status: 'submitted' } },
];

afterEach(() => cleanup());

function renderInbox(onFiltersChange = vi.fn()) {
  render(<MemoryRouter><ConversationInbox conversations={conversations} filters={filters} onFiltersChange={onFiltersChange}
    onRefresh={async () => undefined} onOpen={() => undefined} /></MemoryRouter>);
  return onFiltersChange;
}

describe('Conversation inbox controls', () => {
  it('keeps the current-activity order and hides legacy selectors and multi-selects', () => {
    renderInbox();
    expect(screen.queryByText('Sort & Filter')).toBeNull();
    expect(screen.queryByLabelText('Participation')).toBeNull();
    expect(screen.queryByLabelText('Type')).toBeNull();
    expect(screen.queryByLabelText('Listing or request')).toBeNull();
    expect(screen.queryByLabelText('Conversation partner')).toBeNull();
    expect(screen.queryByLabelText('Minimum offer (₹)')).toBeNull();
  });

  it('lets people clear saved legacy query filters inside the collapsed disclosure', () => {
    const onChange = vi.fn();
    render(<MemoryRouter><ConversationInbox conversations={conversations}
      filters={{ view: 'origin_owner', origin_kind: 'sale_listing', origin_id: ['11111111-1111-4111-8111-111111111111'],
        counterparty_user_id: ['22222222-2222-4222-8222-222222222222'], offer_status: 'submitted',
        offer_min_paise: 500000, sort: 'offer_amount_asc' }} onFiltersChange={onChange}
      onRefresh={async () => undefined} onOpen={() => undefined} /></MemoryRouter>);
    fireEvent.click(screen.getByText('Sort & Filter'));
    fireEvent.click(screen.getByRole('button', { name: 'Clear saved filters' }));
    expect(onChange).toHaveBeenCalledWith({ view: 'all', sort: 'last_activity_desc', marketplace_mode: 'all', group_by: 'item' });
  });

  it('links the whole origin group to its detail while keeping conversation rows separate', () => {
    const onOpen = vi.fn();
    render(<MemoryRouter><ConversationInbox conversations={conversations} filters={filters}
      onFiltersChange={vi.fn()} onRefresh={async () => undefined} onOpen={onOpen} /></MemoryRouter>);
    expect(screen.getByRole('button', { name: 'Show conversations' }).getAttribute('aria-expanded')).toBe('false');
    expect(screen.getByText('3 unread messages')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Open listing' }).getAttribute('href'))
      .toBe('/listings/11111111-1111-4111-8111-111111111111');
    fireEvent.click(screen.getByRole('button', { name: 'Show conversations' }));
    fireEvent.click(screen.getByRole('button', { name: 'Open seller conversation' }));
    expect(onOpen).toHaveBeenCalledWith('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
  });
});
