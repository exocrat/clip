import { describe, expect, it } from 'vitest';
import { inMemoryStore } from '@open-e2ee/signal-protocol-sdk/local/store/memory';
import { ConversationLocalHistory, type ReceivedConversationMessage, type SendConversationMessage } from '../src/features/conversations';
import type { ConversationEntry } from '../../../contracts/generated/types.gen';

const alice = '00000000-0000-4000-8000-000000000001';
const bob = '00000000-0000-4000-8000-000000000002';
const thread = '00000000-0000-4000-8000-000000000003';
const request = (): SendConversationMessage => ({ conversation_id: thread, recipient_user_id: bob,
  operation_id: crypto.randomUUID(), client_timestamp_ms: 100, sender_key_version: 1, recipient_key_version: 1, text: 'Synthetic local text' });
const received = (sequence = 1): ReceivedConversationMessage => ({ message_id: crypto.randomUUID(), sequence,
  sender_user_id: bob, client_timestamp_ms: 100, sender_key_version: 1, recipient_key_version: 1, text: 'Synthetic received text' });
const entry = (): ConversationEntry => ({ entry_id: crypto.randomUUID(), sequence: 2, kind: 'message', sender_user_id: alice,
  created_at: '2026-10-24T00:00:00Z', envelope: { protocol_id: 'open-e2ee-signal', protocol_version: '13.0.0', envelope_version: 1,
    sdk_message_type: 'ciphertext', client_timestamp_ms: 100, sender_key_version: 1, recipient_key_version: 1, payload_base64: 'YQ==' } });
async function fixture() {
  const store = inMemoryStore();
  await store.compareAndSetMetadata('clip:conversation-store-owner:v1', null, alice);
  return { store, history: new ConversationLocalHistory(alice, thread, store) };
}

/** Actual SDK CAS adapter, but memory-only: these tests prove snapshot behavior,
 * not browser IndexedDB reload, quota, eviction or multi-tab durability.
 */
describe('browser-local conversation history', () => {
  it('reopens detached, ordered history and deduplicates received entries', async () => {
    const { history, store } = await fixture();
    const first = received(1);
    await history.put(received(3));
    await history.put(first);
    const { text, ...routing } = first;
    await history.put({ text, ...routing });
    await history.put(first);
    const reopened = new ConversationLocalHistory(alice, thread, store);
    const snapshot = await reopened.read();
    expect(snapshot.received.map((message) => message.sequence)).toEqual([1, 3]);
    snapshot.received[0].text = 'Changed only in caller memory';
    expect((await reopened.read()).received[0].text).toBe(first.text);
    expect((await new ConversationLocalHistory(alice, crypto.randomUUID(), store).read()).received).toEqual([]);
    await expect(new ConversationLocalHistory(bob, thread, store).read()).rejects.toThrow('Local history read failed');
  });

  it('retains outgoing text before sending and binds an idempotent server confirmation', async () => {
    const { history, store } = await fixture();
    const outgoing = request();
    await history.stageSent(outgoing);
    expect((await history.read()).sent[0].confirmation).toBeNull();
    await expect(history.stageSent(outgoing)).rejects.toThrow('write failed');
    const committed = entry();
    const reopened = new ConversationLocalHistory(alice, thread, store);
    await reopened.confirmSent(outgoing.operation_id, committed);
    await reopened.confirmSent(outgoing.operation_id, committed);
    expect((await reopened.read()).sent[0].confirmation?.message_id).toBe(committed.entry_id);
    await expect(reopened.confirmSent(outgoing.operation_id, { ...committed, sender_user_id: bob })).rejects.toThrow();
    await expect(reopened.confirmSent(outgoing.operation_id, { ...committed, sequence: 3 })).rejects.toThrow();
    await expect(history.stageSent({ ...request(), conversation_id: crypto.randomUUID() })).rejects.toThrow();
  });

  it('merges competing CAS writes and rejects conflicting identities or sequences', async () => {
    const { history, store } = await fixture();
    const sibling = new ConversationLocalHistory(alice, thread, store);
    const first = received(1);
    await Promise.all([history.put(first), sibling.put(received(2)), history.stageSent(request())]);
    expect((await history.read()).received.length).toBe(2);
    expect((await history.read()).sent.length).toBe(1);
    await expect(history.put({ ...first, text: 'Conflicting content' })).rejects.toThrow();
    await expect(history.put(received(1))).rejects.toThrow();
  });

  it('rejects malformed local snapshots without exposing their values', async () => {
    const { history, store } = await fixture();
    const key = `clip:history:v1:${alice}:${thread}`;
    await store.compareAndSetMetadata(key, null, '{"secret":"synthetic secret"}');
    await expect(history.read()).rejects.toThrow('Local history read failed');
    await expect(history.put(received())).rejects.toThrow('Local history write failed');
  });

  it('fails closed on quota/storage failure and bounds CAS contention', async () => {
    const { store } = await fixture();
    const broken = new ConversationLocalHistory(alice, thread, { getMetadata: store.getMetadata.bind(store),
      compareAndSetMetadata: async () => { throw new Error('Synthetic sensitive storage diagnostic'); } });
    await expect(broken.stageSent(request())).rejects.toThrow('Local history write failed');
    const busy = new ConversationLocalHistory(alice, thread, { getMetadata: store.getMetadata.bind(store), compareAndSetMetadata: async () => false });
    await expect(busy.put(received())).rejects.toThrow('Local history write failed');
    expect((await new ConversationLocalHistory(alice, thread, store).read()).sent).toEqual([]);
  });

  it('rejects a snapshot copied into another thread and changed account ownership', async () => {
    const { history, store } = await fixture();
    await history.put(received());
    const otherThread = crypto.randomUUID();
    await store.compareAndSetMetadata(`clip:history:v1:${alice}:${otherThread}`, null,
      await store.getMetadata(`clip:history:v1:${alice}:${thread}`));
    await expect(new ConversationLocalHistory(alice, otherThread, store).read()).rejects.toThrow();
    await store.compareAndSetMetadata('clip:conversation-store-owner:v1', alice, bob);
    await expect(history.read()).rejects.toThrow();
    await expect(history.stageSent(request())).rejects.toThrow();
  });
});
