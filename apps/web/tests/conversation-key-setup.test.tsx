// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ConversationKeySetup } from '../src/features/conversations/ConversationKeySetup';
import { ConversationApi, ConversationApiError } from '../src/features/conversations/api';
import { SessionFetchError } from '../src/shared/http/sessionFetch';
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
  it('keeps the marketplace visible during rate limiting and retries without replacing keys', async () => {
    mocks.open.mockRejectedValueOnce(new ConversationApiError(429, 'http')).mockResolvedValue({ stop: mocks.stop }); mount();
    expect(await screen.findByText('Marketplace ready')).toBeTruthy();
    expect(screen.getByRole('alert').textContent).toMatch(/Too many requests/);
    expect(screen.queryByText(/Couldn’t complete encryption setup/)).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('Marketplace ready')).toBeTruthy();
    expect(mocks.open.mock.calls[1][3]).toEqual({});
  });
  it('keeps retry explicit after failure and does not automatically replace keys', async () => {
    mocks.open.mockRejectedValue(new Error('failure')); mount();
    expect(await screen.findByRole('button', { name: 'Retry encryption setup' })).toBeTruthy();
    expect(screen.queryByText('Marketplace ready')).toBeNull();
    expect(mocks.open).toHaveBeenCalledTimes(1);
  });
});


it('preserves a transport rate-limit error for key setup', async () => {
  const api = new ConversationApi(async () => { throw new SessionFetchError(429); });
  await expect(api.readOwnKey()).rejects.toMatchObject({ status: 429, kind: 'http' });
});
