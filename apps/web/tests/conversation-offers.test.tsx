// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ConversationOffers } from '../src/pages/ConversationOffers';
const mocks = vi.hoisted(() => ({ summary: vi.fn(), submit: vi.fn(), withdraw: vi.fn(), fetch: vi.fn() }));
vi.mock('../src/features/conversations', () => ({ ConversationApi: class { readSummary = mocks.summary; } }));
vi.mock('../src/features/listings', () => ({ submitListingOffer: mocks.submit, withdrawListingOffer: mocks.withdraw, ListingsApiError: class extends Error { constructor(readonly status: number) { super('Conflict'); } } }));
vi.mock('../src/shared/http/sessionFetch', () => ({ sessionFetch: mocks.fetch }));
const current = { offer_id: '33333333-3333-4333-8333-333333333333', revision: 2, amount_paise: 50000, status: 'submitted', updated_at: '2026-10-28T00:00:00Z', note_envelope: null };
beforeEach(() => {
  vi.clearAllMocks();
  mocks.summary.mockResolvedValue({ origin_id: 'listing', origin_kind: 'sale_listing', caller_role: 'initiator' });
  mocks.fetch.mockImplementation(async () => new Response(JSON.stringify(current)));
  mocks.submit.mockResolvedValue({ ...current, revision: 3 });
  mocks.withdraw.mockResolvedValue({ ...current, status: 'withdrawn', revision: 3 });
});
afterEach(cleanup);
describe('connected sale offer actions', () => {
  it('submits whole rupees through the Listings boundary with the current revision', async () => {
    render(<ConversationOffers conversationId="chat" />);
    fireEvent.change(await screen.findByLabelText('Offer amount (₹)'), { target: { value: '650' } });
    fireEvent.click(screen.getByRole('button', { name: 'Update offer' }));
    await waitFor(() => expect(mocks.submit).toHaveBeenCalledWith('listing', 'chat', expect.objectContaining({ amount_paise: 65000, expected_revision: 2 })));
  });
  it('withdraws the exact current offer and revision', async () => {
    render(<ConversationOffers conversationId="chat" />);
    fireEvent.click(await screen.findByRole('button', { name: 'Withdraw offer' }));
    await waitFor(() => expect(mocks.withdraw).toHaveBeenCalledWith('listing', 'chat', expect.objectContaining({ offer_id: current.offer_id, expected_revision: 2 })));
    expect(await screen.findByText('Offer withdrawn.')).toBeTruthy();
  });
  it('retains an identical operation for an uncertain-write retry', async () => {
    mocks.submit.mockRejectedValueOnce(new Error('transport'));
    render(<ConversationOffers conversationId="chat" />);
    fireEvent.click(await screen.findByRole('button', { name: 'Update offer' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Retry offer change' }));
    await waitFor(() => expect(mocks.submit).toHaveBeenCalledTimes(2));
    expect(mocks.submit.mock.calls[0]).toEqual(mocks.submit.mock.calls[1]);
  });
  it('shows seller read access and no buyer command, and hides offers for Wanted', async () => {
    mocks.summary.mockResolvedValue({ origin_kind: 'sale_listing', caller_role: 'origin_owner' });
    const view = render(<ConversationOffers conversationId="chat" />);
    expect(await screen.findByText('₹500 · Submitted')).toBeTruthy();
    expect(screen.queryByLabelText('Offer amount (₹)')).toBeNull();
    view.unmount();
    mocks.summary.mockResolvedValue({ origin_kind: 'wanted_request', caller_role: 'initiator' });
    render(<ConversationOffers conversationId="wanted" />);
    await waitFor(() => expect(mocks.summary).toHaveBeenLastCalledWith('wanted', expect.any(AbortSignal)));
    expect(screen.queryByRole('region', { name: 'Sale offer' })).toBeNull();
  });
});
