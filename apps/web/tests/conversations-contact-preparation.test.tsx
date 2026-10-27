// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ConversationContactPreparation } from '../src/features/conversations/ConversationContactPreparation';
import { ConversationApi, ConversationApiError } from '../src/features/conversations/api';

const conversationId = '11111111-1111-4111-8111-111111111111';
afterEach(cleanup);

describe('explicit own-contact preparation', () => {
  it('requires exact selection and confirmation, then keeps values out of the UI', async () => {
    const api = { readContactOptions: vi.fn(async () => ({ email_available: true, phone_available: true, upi_available: false })),
      prepareOwnContacts: vi.fn(async () => ({ email: 'synthetic@example.invalid', phone: null, upi_id: null })) };
    render(<ConversationContactPreparation conversationId={conversationId} api={api} />);
    expect(api.readContactOptions).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Choose contact details' }));
    const email = await screen.findByRole('checkbox', { name: 'Email' });
    expect((screen.getByRole('checkbox', { name: 'UPI ID (not set)' }) as HTMLInputElement).disabled).toBe(true);
    fireEvent.click(email);
    fireEvent.click(screen.getByRole('button', { name: 'Review selected details' }));
    expect(api.prepareOwnContacts).not.toHaveBeenCalled();
    expect(screen.getByText('Confirm for this conversation: Email.')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Confirm selected details' }));
    await screen.findByText(/Selection checked. Nothing has been sent/);
    expect(api.prepareOwnContacts).toHaveBeenCalledWith(conversationId, ['email'], expect.any(AbortSignal));
    expect(screen.queryByText('synthetic@example.invalid')).toBeNull();
  });

  it('cancels without retrieving values and shows dependency failure without private diagnostics', async () => {
    const api = { readContactOptions: vi.fn(async () => ({ email_available: true, phone_available: false, upi_available: false })),
      prepareOwnContacts: vi.fn(async () => { throw new Error('private-detail'); }) };
    render(<ConversationContactPreparation conversationId={conversationId} api={api} />);
    fireEvent.click(screen.getByRole('button', { name: 'Choose contact details' }));
    fireEvent.click(await screen.findByRole('checkbox', { name: 'Email' }));
    fireEvent.click(screen.getByRole('button', { name: 'Review selected details' }));
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(api.prepareOwnContacts).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Choose contact details' }));
    fireEvent.click(await screen.findByRole('checkbox', { name: 'Email' }));
    fireEvent.click(screen.getByRole('button', { name: 'Review selected details' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm selected details' }));
    await screen.findByText(/Couldn’t prepare.*Nothing has been sent/);
    expect(screen.queryByText('private-detail')).toBeNull();
  });

  it('validates the selected-only API response and passes exact fields to the member route', async () => {
    let leak = false;
    const transport = vi.fn(async () => new Response(JSON.stringify({ email: 'synthetic@example.invalid',
      phone: leak ? 'private-unselected' : null, upi_id: null }), { headers: { 'Content-Type': 'application/json' } }));
    const api = new ConversationApi(transport);
    await api.prepareOwnContacts(conversationId, ['email']);
    expect(transport).toHaveBeenCalledWith(`/conversations/${conversationId}/contact-preparations`,
      expect.objectContaining({ method: 'POST', cache: 'no-store', body: JSON.stringify({ fields: ['email'] }) }));
    leak = true;
    await expect(api.prepareOwnContacts(conversationId, ['email'])).rejects.toBeInstanceOf(ConversationApiError);
    expect(() => api.prepareOwnContacts(conversationId, ['email', 'email'])).toThrow(ConversationApiError);
  });
});
