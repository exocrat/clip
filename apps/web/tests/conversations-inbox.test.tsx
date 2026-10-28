// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ConversationInbox, type ConversationInboxFilters, type ConversationInboxItem } from '../src/features/conversations';

const filters: ConversationInboxFilters = { view: 'all', sort: 'last_activity_desc' };
const conversations: ConversationInboxItem[] = [
  { conversation_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', label: 'Sale listing conversation',
    role: 'seller', last_activity_at: '2026-10-27T00:00:00Z', unread_count: 0,
    origin_kind: 'sale_listing', origin_id: '11111111-1111-4111-8111-111111111111',
    counterparty_user_id: '22222222-2222-4222-8222-222222222222',
    current_offer: { amount_paise: 500000, status: 'submitted' } },
];

afterEach(() => cleanup());

function renderInbox(onFiltersChange = vi.fn()) {
  render(<ConversationInbox conversations={conversations} filters={filters} onFiltersChange={onFiltersChange}
    onRefresh={async () => undefined} onOpen={() => undefined} />);
  return onFiltersChange;
}

describe('Conversation inbox controls', () => {
  it('keeps role and origin type single-choice while applying multiple origin and partner choices together', () => {
    const onChange = renderInbox();
    fireEvent.change(screen.getByLabelText('Participation'), { target: { value: 'initiated' } });
    expect(onChange).toHaveBeenLastCalledWith({ ...filters, view: 'initiated' });

    fireEvent.change(screen.getByLabelText('Type'), { target: { value: 'sale_listing' } });
    expect(onChange).toHaveBeenLastCalledWith({ ...filters, origin_kind: 'sale_listing', origin_id: undefined });

    fireEvent.click(screen.getByText('All origins'));
    fireEvent.click(screen.getByRole('checkbox', { name: 'Sale listing · 11111111…1111' }));
    fireEvent.click(screen.getByText('All partners'));
    fireEvent.click(screen.getByRole('checkbox', { name: 'Partner · 22222222…2222' }));
    fireEvent.click(screen.getByRole('button', { name: 'Apply origin and partner filters' }));
    expect(onChange).toHaveBeenLastCalledWith({ ...filters,
      origin_id: ['11111111-1111-4111-8111-111111111111'],
      counterparty_user_id: ['22222222-2222-4222-8222-222222222222'] });
  });

  it('converts whole-rupee offer bounds to paise and rejects invalid ranges', () => {
    const onChange = renderInbox();
    fireEvent.change(screen.getByLabelText('Minimum offer (₹)'), { target: { value: '5000' } });
    fireEvent.change(screen.getByLabelText('Maximum offer (₹)'), { target: { value: '7000' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply amount range' }));
    expect(onChange).toHaveBeenLastCalledWith({ ...filters, offer_min_paise: 500000, offer_max_paise: 700000 });

    fireEvent.change(screen.getByLabelText('Minimum offer (₹)'), { target: { value: '8000' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply amount range' }));
    expect(screen.getByRole('alert').textContent).toContain('must not exceed');
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it('clears offer state when switching to Wanted Requests and keeps amount controls disabled there', () => {
    const onChange = vi.fn();
    render(<ConversationInbox conversations={conversations}
      filters={{ view: 'all', origin_kind: 'sale_listing', offer_status: 'submitted', offer_min_paise: 500000,
        sort: 'offer_amount_asc' }} onFiltersChange={onChange} onRefresh={async () => undefined} onOpen={() => undefined} />);
    fireEvent.change(screen.getByLabelText('Type'), { target: { value: 'wanted_request' } });
    expect(onChange).toHaveBeenCalledWith({ view: 'all', origin_kind: 'wanted_request', origin_id: undefined,
      offer_status: undefined, offer_min_paise: undefined, offer_max_paise: undefined, sort: 'last_activity_desc' });
  });
});
