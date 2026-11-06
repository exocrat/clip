// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import type { ConversationThreadProps } from '../src/features/conversations/ConversationThread';
import { ConversationDetailPage, ConversationPageRuntimeProvider, type ConversationPageRuntime } from '../src/features/conversations/ConversationPages';

// Exercise the real page's polling/cursor/window logic with reviewed API shapes;
// crypto and the timer-driven presentation are isolated from this regression.
vi.mock('../src/features/conversations/relay', () => ({
  openIndexedDbConversationSession: vi.fn(async () => ({
    stop: vi.fn(async () => undefined),
    crypto: { resumeParticipantSession: vi.fn(async () => true) },
    history: { read: vi.fn(async () => ({ received: [], sent: [] })) },
  })),
}));
vi.mock('../src/features/conversations/ConversationContactPreparation', () => ({ ConversationContactPreparation: () => null }));
let thread: ConversationThreadProps;
vi.mock('../src/features/conversations/ConversationThread', () => ({
  ConversationThread: (props: ConversationThreadProps) => {
    thread = props;
    return <output data-testid="window">{props.entries.map(e => e.sequence).join(',')}</output>;
  },
}));
afterEach(() => cleanup());

it('continues receiving beyond 400 entries while keeping an older page separate and bounded', async () => {
  const own = '11111111-1111-4111-8111-111111111111';
  const peer = '22222222-2222-4222-8222-222222222222';
  const conversationId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
  let availableThrough = 460;
  const readEntries = vi.fn(async (_id: string, after: number, _signal?: AbortSignal, size = 20) => {
    const end = Math.min(availableThrough, after + size);
    return { items: Array.from({ length: Math.max(0, end - after) }, (_, i) => ({
      entry_id: `00000000-0000-4000-8000-${String(after + i + 1).padStart(12, '0')}`,
      sequence: after + i + 1, sender_user_id: peer, kind: 'message',
      created_at: '2026-11-06T00:00:00Z', content_deleted: true, envelope: null,
    })), scanned_through_sequence: Math.max(after, end), has_more: end < availableThrough };
  });
  const api = {
    readSummary: vi.fn(async () => ({ conversation_id: conversationId, caller_role: 'initiator',
      initiator_user_id: own, counterparty_user_id: peer, origin_kind: 'sale_listing',
      origin_id: '33333333-3333-4333-8333-333333333333', own_last_read_sequence: 0, unread_count: 460 })),
    readOwnKey: vi.fn(async () => ({ user_id: own, key_version: 1 })),
    readMemberKeys: vi.fn(async () => ({ members: [{ user_id: peer, key_version: 1 }] })),
    readState: vi.fn(async () => ({ own_last_read_sequence: 0 })), readEntries,
  };
  const runtime = { userId: own, api, listingSelection: {}, listingAvailability: {} } as unknown as ConversationPageRuntime;
  render(<MemoryRouter><ConversationPageRuntimeProvider runtime={runtime}>
    <ConversationDetailPage conversationId={conversationId} />
  </ConversationPageRuntimeProvider></MemoryRouter>);
  await waitFor(() => expect(thread.key_state.kind).toBe('ready'));
  for (let page = 0; page < 23; page++) await act(async () => { await thread.onRefresh(); });
  expect(thread.entries).toHaveLength(400);
  expect(thread.entries[0].sequence).toBe(61);
  expect(thread.entries.at(-1)?.sequence).toBe(460);
  expect(readEntries).toHaveBeenCalledTimes(23);

  fireEvent.click(screen.getByRole('button', { name: 'Load earlier messages' }));
  await screen.findByRole('button', { name: 'Return to latest messages' });
  const historicalWindow = screen.getByTestId('window').textContent;
  expect(thread.entries[0].sequence).toBe(1);
  availableThrough = 480;
  await act(async () => { await thread.onRefresh(); });
  expect(readEntries).toHaveBeenLastCalledWith(conversationId, 460);
  expect(screen.getByTestId('window').textContent).toBe(historicalWindow);
  expect(thread.entries).toHaveLength(400);

  fireEvent.click(screen.getByRole('button', { name: 'Return to latest messages' }));
  expect(thread.entries).toHaveLength(400);
  expect(thread.entries[0].sequence).toBe(81);
  expect(thread.entries.at(-1)?.sequence).toBe(480);
  expect(thread.latest_view_revision).toBe(1);
  availableThrough = 500;
  await act(async () => { await thread.onRefresh(); });
  expect(thread.entries.at(-1)?.sequence).toBe(500);
  expect(thread.entries).toHaveLength(400);
});
