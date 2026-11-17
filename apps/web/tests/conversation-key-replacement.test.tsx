// @vitest-environment jsdom
import { act, cleanup, render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import type { ConversationThreadProps } from '../src/features/conversations/ConversationThread';
import { ConversationDetailPage, ConversationPageRuntimeProvider, type ConversationPageRuntime } from '../src/features/conversations/ConversationPages';

const fixture = vi.hoisted(() => ({
  receive: vi.fn(async () => ({ text: 'New encrypted message' })),
  send: vi.fn(async () => ({ message_id: 'accepted' })),
}));
vi.mock('../src/features/conversations/relay', () => ({
  openIndexedDbConversationSession: vi.fn(async () => ({
    stop: vi.fn(async () => undefined),
    crypto: { resumeParticipantSession: vi.fn(async () => true) },
    history: { read: vi.fn(async () => ({ received: [], sent: [] })) },
    receiveText: fixture.receive, sendText: fixture.send,
  })),
}));
vi.mock('../src/features/conversations/ConversationContactPreparation', () => ({ ConversationContactPreparation: () => null }));
let thread: ConversationThreadProps;
vi.mock('../src/features/conversations/ConversationThread', () => ({
  ConversationThread: (props: ConversationThreadProps) => { thread = props; return <output>{props.entries.length}</output>; },
}));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

async function openThread() {
  const own = '11111111-1111-4111-8111-111111111111';
  const peer = '22222222-2222-4222-8222-222222222222';
  const id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
  const readEntries = vi.fn(async () => ({ items: [1, 2].map(sequence => ({
    entry_id: `entry-${sequence}`, sequence, sender_user_id: peer, kind: 'message',
    created_at: '2026-11-06T00:00:00Z', content_deleted: false,
    envelope: { sender_key_version: 1, recipient_key_version: sequence },
  })), scanned_through_sequence: 2, has_more: false }));
  const api = {
    readSummary: vi.fn(async () => ({ conversation_id: id, caller_role: 'initiator', initiator_user_id: own,
      counterparty_user_id: peer, origin_kind: 'sale_listing', origin_id: '33333333-3333-4333-8333-333333333333' })),
    readOwnKey: vi.fn(async () => ({ user_id: own, key_version: 2 })),
    readMemberKeys: vi.fn(async () => ({ members: [{ user_id: peer, key_version: 1 }] })),
    readState: vi.fn(async () => ({ own_last_read_sequence: 0 })), readEntries,
  };
  const runtime = { userId: own, api, listingSelection: {}, listingAvailability: {} } as unknown as ConversationPageRuntime;
  render(<MemoryRouter><ConversationPageRuntimeProvider runtime={runtime}>
    <ConversationDetailPage conversationId={id} />
  </ConversationPageRuntimeProvider></MemoryRouter>);
  await waitFor(() => expect(thread.key_state.kind).toBe('ready'));
  return { readEntries, readOwnKey: api.readOwnKey };
}

it('continues past a previous-key message and displays a current-key message', async () => {
  await openThread();
  await act(async () => { await thread.onRefresh(); });
  expect(fixture.receive).toHaveBeenCalledOnce();
  expect(thread.entries.map(entry => entry.text)).toEqual([
    'This message is unavailable because your encryption key has changed.', 'New encrypted message',
  ]);
});

it('still rejects current-key decryption errors and does not misreport an accepted send', async () => {
  fixture.receive.mockRejectedValueOnce(new Error('Synthetic current-key failure'));
  const { readEntries } = await openThread();
  await act(async () => { await expect(thread.onRefresh()).rejects.toThrow('Synthetic current-key failure'); });
  expect(thread.entries).toHaveLength(0);
  fixture.receive.mockRejectedValueOnce(new Error('Synthetic current-key failure'));
  await act(async () => { await expect(thread.onSend('Synthetic message', '00000000-0000-4000-8000-000000000001')).resolves.toBeUndefined(); });
  expect(fixture.send).toHaveBeenCalledOnce();
  expect(readEntries).toHaveBeenCalledTimes(2);
});


it('stops an old browser before reading entries after its account key changes', async () => {
  const { readEntries, readOwnKey } = await openThread();
  readOwnKey.mockResolvedValueOnce({ user_id: '11111111-1111-4111-8111-111111111111', key_version: 3 });
  await act(async () => { await thread.onRefresh(); });
  expect(thread.key_state.kind).toBe('key_state_lost');
  expect(readEntries).not.toHaveBeenCalled();
});
