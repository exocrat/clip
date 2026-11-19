// @vitest-environment jsdom
import { act, cleanup, render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import type { ConversationThreadProps } from '../src/features/conversations/ConversationThread';
import { RejectedConversationControlError } from '../src/features/conversations/crypto';
import { ConversationDetailPage, ConversationPageRuntimeProvider, type ConversationPageRuntime } from '../src/features/conversations/ConversationPages';

const control = vi.hoisted(() => vi.fn());
vi.mock('../src/features/conversations/relay', () => ({
  openIndexedDbConversationSession: vi.fn(async () => ({
    stop: vi.fn(async () => undefined),
    crypto: { resumeParticipantSession: vi.fn(async () => true), receiveProtocolEntry: control },
    history: { read: vi.fn(async () => ({ received: [], sent: [] })) },
  })),
}));
vi.mock('../src/features/conversations/ConversationContactPreparation', () => ({ ConversationContactPreparation: () => null }));
let thread: ConversationThreadProps;
vi.mock('../src/features/conversations/ConversationThread', () => ({ ConversationThread: (props: ConversationThreadProps) => {
  thread = props;
  return <output>{props.entries.map(e => e.sequence).join(',')}</output>;
} }));
afterEach(() => { cleanup(); control.mockReset(); });

/** Isolate page error classification; real SDK and API acceptance have separate integration checks. */
async function mount(lastRead = 0) {
  const own = '11111111-1111-4111-8111-111111111111';
  const peer = '22222222-2222-4222-8222-222222222222';
  const id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
  const row = (sequence: number) => ({ entry_id: `00000000-0000-4000-8000-${String(sequence).padStart(12, '0')}`,
    sequence, sender_user_id: peer, kind: 'message', created_at: '2026-11-19T00:00:00Z', content_deleted: true, envelope: null });
  const poisoned = { ...row(2), kind: 'protocol_control', content_deleted: false,
    recovery_target: { entry_id: row(1).entry_id, sequence: 1, sender_user_id: own, created_at: row(1).created_at },
    envelope: { envelope_version: 2, recipient_key_version: null } };
  const readEntries = vi.fn(async (_id: string, after: number) => ({ items: after < 3 ? [row(1), poisoned, row(3)] : [], scanned_through_sequence: 3, has_more: false }));
  const api = { readSummary: vi.fn(async () => ({ conversation_id: id, caller_role: 'initiator', initiator_user_id: own,
    counterparty_user_id: peer, origin_kind: 'sale_listing', origin_id: id, own_last_read_sequence: 0, unread_count: 2 })),
    readOwnKey: vi.fn(async () => ({ user_id: own, key_version: 1 })),
    readMemberKeys: vi.fn(async () => ({ members: [{ user_id: peer, key_version: 1 }] })),
    readState: vi.fn(async () => ({ own_last_read_sequence: lastRead })), readEntries };
  render(<MemoryRouter><ConversationPageRuntimeProvider runtime={{ userId: own, api, listingSelection: {}, listingAvailability: {} } as unknown as ConversationPageRuntime}>
    <ConversationDetailPage conversationId={id} />
  </ConversationPageRuntimeProvider></MemoryRouter>);
  await waitFor(() => expect(thread.key_state.kind).toBe('ready'));
  return { readEntries, id };
}

it('skips a definitively rejected control, displays later entries and advances the cursor', async () => {
  control.mockRejectedValue(new RejectedConversationControlError('Invalid peer recovery data'));
  const { readEntries, id } = await mount();
  await act(async () => { await thread.onRefresh(); });
  expect(thread.entries.map(e => e.sequence)).toEqual([1, 3]);
  await act(async () => { await thread.onRefresh(); });
  expect(readEntries).toHaveBeenLastCalledWith(id, 3);
  expect(control).toHaveBeenCalledTimes(1);
});

it('retries transient controls independently without withholding visible messages', async () => {
  control.mockRejectedValueOnce(new Error('Synthetic temporary storage failure')).mockResolvedValue('handled');
  const { readEntries, id } = await mount();
  await act(async () => { await thread.onRefresh(); });
  expect(thread.entries.map(e => e.sequence)).toEqual([1, 3]);
  await act(async () => { await thread.onRefresh(); });
  expect(readEntries).toHaveBeenCalledWith(id, 1);
  expect(readEntries).toHaveBeenLastCalledWith(id, 3);
  expect(thread.entries.map(e => e.sequence)).toEqual([1, 3]);
});


it('keeps a persistently pending control from blocking messages across repeated polls', async () => {
  control.mockRejectedValue(new Error('Synthetic pending SDK control'));
  const { readEntries, id } = await mount();
  for (let poll = 0; poll < 4; poll++) {
    await act(async () => { await thread.onRefresh(); });
    expect(thread.entries.map(e => e.sequence)).toEqual([1, 3]);
  }
  expect(control).toHaveBeenCalledTimes(4);
  expect(readEntries).toHaveBeenCalledTimes(7);
  expect(readEntries).toHaveBeenLastCalledWith(id, 3);
});

it('bounds retry work and revisits later failed controls while new traffic continues', async () => {
  control.mockRejectedValue(new Error('Synthetic persistent control failure'));
  const { readEntries, id } = await mount();
  const initial = await readEntries.getMockImplementation()?.(id, 0);
  if (!initial) throw new Error('Expected reviewed fixture');
  let available = 20;
  readEntries.mockImplementation(async (_id, after) => {
    const through = Math.min(after + 20, available);
    const items = Array.from({ length: Math.max(0, through - after) }, (_, offset) => {
      const sequence = after + offset + 1;
      const value = sequence === 2 || sequence === 42 ? initial.items[1] : initial.items[0];
      return { ...value, sequence, entry_id: `00000000-0000-4000-8000-${String(sequence).padStart(12, '0')}` };
    });
    return { items, scanned_through_sequence: through, has_more: through < available };
  });
  for (let poll = 0; poll < 8; poll++) {
    available = (poll + 1) * 20;
    const before = readEntries.mock.calls.length;
    await act(async () => { await thread.onRefresh(); });
    expect(readEntries.mock.calls.length - before).toBeLessThanOrEqual(2);
    expect(thread.entries.at(-1)?.sequence).toBe(available);
  }
  expect(control.mock.calls.filter(([context]) => context.sequence === 42).length).toBeGreaterThanOrEqual(2);
  expect(thread.entries).toHaveLength(158);
});


it('revisits historical controls after restart without rewinding visible messages', async () => {
  control.mockRejectedValue(new Error('Synthetic pending control'));
  const { readEntries, id } = await mount(60);
  const initial = await readEntries.getMockImplementation()?.(id, 0);
  if (!initial) throw new Error('Expected reviewed fixture');
  readEntries.mockImplementation(async (_id, after) => {
    const through = Math.min(after + 20, 65);
    const items = Array.from({ length: Math.max(0, through - after) }, (_, offset) => {
      const sequence = after + offset + 1;
      return { ...(sequence === 2 ? initial.items[1] : initial.items[0]), sequence,
        entry_id: `00000000-0000-4000-8000-${String(sequence).padStart(12, '0')}` };
    });
    return { items, scanned_through_sequence: through, has_more: through < 65 };
  });
  await act(async () => { await thread.onRefresh(); });
  expect(readEntries).toHaveBeenCalledWith(id, 0);
  expect(readEntries).toHaveBeenCalledWith(id, 55);
  expect(thread.entries[0].sequence).toBe(56);
  expect(thread.entries.at(-1)?.sequence).toBe(65);
  expect(control).toHaveBeenCalledTimes(1);
});
