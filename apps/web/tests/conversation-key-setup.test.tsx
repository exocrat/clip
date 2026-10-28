// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ConversationKeySetup } from '../src/features/conversations/ConversationKeySetup';
import { KeyRegistrationAcknowledgementRequiredError } from '../src/features/conversations/crypto';
const mocks = vi.hoisted(() => ({ open: vi.fn(), stop: vi.fn(async () => undefined) }));
vi.mock('../src/features/conversations/relay', () => ({ openIndexedDbConversationSession: mocks.open }));
const actor = '11111111-1111-4111-8111-111111111111';
function mount() { render(<MemoryRouter><ConversationKeySetup userId={actor}><p>Marketplace ready</p></ConversationKeySetup></MemoryRouter>); }
afterEach(cleanup);
beforeEach(() => vi.clearAllMocks());
describe('first-device account messaging setup', () => {
  it('resumes existing keys without showing consent again', async () => {
    mocks.open.mockResolvedValue({ stop: mocks.stop }); mount();
    expect(await screen.findByText('Marketplace ready')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Create encryption key' })).toBeNull();
    expect(mocks.stop).toHaveBeenCalledTimes(1);
  });
  it('publishes only after the user checks consent and explicitly creates keys', async () => {
    mocks.open.mockRejectedValueOnce(new KeyRegistrationAcknowledgementRequiredError()).mockResolvedValue({ stop: mocks.stop }); mount();
    const create = await screen.findByRole('button', { name: 'Create encryption key' });
    expect((create as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole('checkbox'));
    expect(mocks.open).toHaveBeenCalledTimes(1);
    fireEvent.click(create);
    expect(await screen.findByText('Marketplace ready')).toBeTruthy();
    expect(mocks.open.mock.calls[1][3]).toEqual({ acknowledgeUnrecoverableHistoryRisk: true });
  });
  it('keeps retry explicit after failure and does not automatically replace keys', async () => {
    mocks.open.mockRejectedValue(new Error('failure')); mount();
    expect(await screen.findByRole('button', { name: 'Retry encryption setup' })).toBeTruthy();
    expect(screen.queryByText('Marketplace ready')).toBeNull();
    expect(mocks.open).toHaveBeenCalledTimes(1);
  });
});
