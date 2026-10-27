import { describe, expect, it, vi } from 'vitest';
import { inMemoryStore } from '@open-e2ee/signal-protocol-sdk/local/store/memory';
import type { Envelope } from '@open-e2ee/signal-protocol-sdk';
import type {
  ContactShareRequest, ConversationEntry, KeyBundle, MemberPreKeyBundle, MessageRequest,
  PublicKeyBundleRequest, PublicPreKeyBatchRequest, PublicPreKeyMaterial,
} from '../../../contracts/generated/types.gen';
import {
  ConversationApi, ConversationCryptoError, ConversationKeyStateLostError,
  ConversationRelay, KeyRegistrationAcknowledgementRequiredError, createConversationSession,
  type ConversationSession, type ConversationEnvelopeRoute,
} from '../src/features/conversations';
import { processProtocolControlEntry } from '../src/features/conversations/ConversationPages';

const alice = '00000000-0000-4000-8000-000000000001';
const bob = '00000000-0000-4000-8000-000000000002';
const mallory = '00000000-0000-4000-8000-000000000003';
const thread = '00000000-0000-4000-8000-000000000004';
const reply = (value: unknown, status = 200) => new Response(JSON.stringify(value), {
  status, headers: { 'Content-Type': 'application/json' },
});

/** Reviewed HTTP-contract double only. Crypto and SDK local stores below are real.
 * This is not a production auth implementation or evidence of PostgreSQL integration.
 */
class RelayHttpFixture {
  keys = new Map<string, KeyBundle[]>();
  prekeys = new Map<string, PublicPreKeyMaterial[]>();
  operations = new Map<string, { request: string; result: unknown }>();
  entries: ConversationEntry[] = [];
  submitted: string[] = [];
  published: string[] = [];
  loseNextMessageReply = false;
  loseNextPublicationReply = false;
  failNextPublicationBeforeCommit = false;

  api(actor: string) {
    return new ConversationApi(async (path, init) => {
      const url = new URL(path, 'http://127.0.0.1');
      const current = (user: string) => this.keys.get(user)?.at(-1) ?? null;
      const inventory = (user: string) => {
        const version = current(user)?.key_version;
        const available = this.prekeys.get(`${user}:${version}`) ?? [];
        return { key_version: version, ec_one_time_count: available.filter((key) => key.key_type === 'ecPreKey').length,
          kem_one_time_count: available.filter((key) => key.key_type === 'kemOneTimePreKey').length };
      };
      const payload: unknown = init.body ? JSON.parse(String(init.body)) : null;
      if (url.pathname === '/me/conversation-key' && init.method === 'GET') return reply(current(actor));
      if (url.pathname === '/me/conversation-key' && init.method === 'PUT') {
        const request = payload as PublicKeyBundleRequest;
        const key = `${actor}:${request.operation_id}`;
        const saved = this.operations.get(key);
        if (saved) return saved.request === JSON.stringify(request) ? reply(saved.result) : reply({}, 409);
        const { operation_id: _operation, ...material } = request;
        const bundle: KeyBundle = { ...material, user_id: actor, key_version: (current(actor)?.key_version ?? 0) + 1 };
        this.keys.set(actor, [...(this.keys.get(actor) ?? []), bundle]);
        const result = { user_id: actor, key_version: bundle.key_version, protocol_id: bundle.protocol_id, protocol_version: bundle.protocol_version };
        this.operations.set(key, { request: JSON.stringify(request), result });
        return reply(result);
      }
      if (url.pathname === '/me/conversation-prekeys') {
        if (!current(actor)) return reply({}, 409);
        if (init.method === 'GET') return reply(inventory(actor));
        const request = payload as PublicPreKeyBatchRequest;
        this.published.push(JSON.stringify(request));
        if (this.failNextPublicationBeforeCommit) {
          this.failNextPublicationBeforeCommit = false;
          return reply({}, 503);
        }
        const key = `${actor}:${request.operation_id}`;
        const saved = this.operations.get(key);
        if (saved) return saved.request === JSON.stringify(request) ? reply(saved.result) : reply({}, 409);
        if (request.key_version !== current(actor)?.key_version) return reply({}, 409);
        const available = this.prekeys.get(`${actor}:${request.key_version}`) ?? [];
        if (request.prekeys.some((key) => available.some((old) => old.key_id === key.key_id && old.key_type === key.key_type))) return reply({}, 409);
        this.prekeys.set(`${actor}:${request.key_version}`, [...available, ...request.prekeys]);
        const result = inventory(actor);
        this.operations.set(key, { request: JSON.stringify(request), result });
        if (this.loseNextPublicationReply) {
          this.loseNextPublicationReply = false;
          throw new Error('Synthetic lost response after commit');
        }
        return reply(result);
      }
      if (![alice, bob].includes(actor) || !url.pathname.startsWith(`/conversations/${thread}`)) return reply({}, 404);
      const peer = actor === alice ? bob : alice;
      if (url.pathname === `/conversations/${thread}`) return reply({
        conversation_id: thread, origin_kind: 'sale_listing', origin_id: crypto.randomUUID(),
        initiator_user_id: alice, caller_role: actor === alice ? 'initiator' : 'origin_owner',
        counterparty_user_id: peer, last_activity_at: new Date().toISOString(),
        own_last_read_sequence: 0, unread_count: 0, current_offer: null,
      });
      if (url.pathname.endsWith('/keys')) {
        if (!current(alice) || !current(bob)) return reply({}, 409);
        return reply({ members: [...(this.keys.get(alice) ?? []), ...(this.keys.get(bob) ?? [])] });
      }
      if (url.pathname.endsWith('/prekey-bundle')) {
        const request = payload as { operation_id: string };
        const key = `${actor}:${request.operation_id}`;
        const saved = this.operations.get(key);
        if (saved) return reply(saved.result);
        const bundle = current(peer);
        if (!bundle) return reply({}, 409);
        const available = this.prekeys.get(`${peer}:${bundle.key_version}`) ?? [];
        const take = (type: PublicPreKeyMaterial['key_type']) => {
          const index = available.findIndex((key) => key.key_type === type);
          return index < 0 ? null : available.splice(index, 1)[0];
        };
        const result: MemberPreKeyBundle = { key_bundle: bundle, registration_id: bundle.registration_id, device_id: 1,
          ec_one_time_prekey: take('ecPreKey'), kem_one_time_prekey: take('kemOneTimePreKey') };
        this.operations.set(key, { request: JSON.stringify(request), result });
        return reply(result);
      }
      if (url.pathname.endsWith('/messages')) {
        const request = payload as MessageRequest;
        this.submitted.push(JSON.stringify(request));
        const key = `${actor}:${request.operation_id}`;
        const saved = this.operations.get(key);
        if (saved) return saved.request === JSON.stringify(request) ? reply(saved.result) : reply({}, 409);
        const recovery = request.envelope.recovery_for_entry_id == null ? null :
          this.entries.find((item) => item.entry_id === request.envelope.recovery_for_entry_id) ?? null;
        const entry: ConversationEntry = { entry_id: crypto.randomUUID(), sequence: this.entries.length + 1,
          kind: request.envelope.sdk_message_type === 'retry_request' || recovery ? 'protocol_control' : 'message',
          sender_user_id: actor, created_at: new Date().toISOString(), content_deleted: false,
          envelope: request.envelope,
          ...(recovery ? { recovery_target: { entry_id: recovery.entry_id, sequence: recovery.sequence,
            sender_user_id: recovery.sender_user_id, created_at: recovery.created_at } } : {}),
        };
        this.entries.push(entry);
        this.operations.set(key, { request: JSON.stringify(request), result: entry });
        if (this.loseNextMessageReply) {
          this.loseNextMessageReply = false;
          throw new Error('Synthetic lost response after commit');
        }
        return reply(entry, 201);
      }
      if (url.pathname.endsWith('/contact-shares')) {
        const request = payload as ContactShareRequest;
        this.submitted.push(JSON.stringify(request));
        const key = `${actor}:${request.operation_id}`;
        const saved = this.operations.get(key);
        if (saved) return saved.request === JSON.stringify(request) ? reply(saved.result) : reply({}, 409);
        const entry: ConversationEntry = { entry_id: crypto.randomUUID(), sequence: this.entries.length + 1,
          kind: 'contact_share', sender_user_id: actor, created_at: new Date().toISOString(),
          content_deleted: false, envelope: request.envelope };
        this.entries.push(entry);
        this.operations.set(key, { request: JSON.stringify(request), result: entry });
        if (this.loseNextMessageReply) {
          this.loseNextMessageReply = false;
          throw new Error('Synthetic lost response after commit');
        }
        return reply(entry, 201);
      }
      return reply({}, 404);
    });
  }
}

async function establish(sender: ConversationSession, server: RelayHttpFixture, senderId: string, recipientId: string) {
  const member = await server.api(senderId).consumeMemberPrekeys(thread, { operation_id: crypto.randomUUID() });
  await sender.crypto.establishParticipantSession(member, { userId: recipientId, keyVersion: member.key_bundle.key_version });
}

const message = (recipientId: string, operation = crypto.randomUUID()) => ({
  conversation_id: thread, recipient_user_id: recipientId,
  operation_id: operation, client_timestamp_ms: Date.now(),
  sender_key_version: 1, recipient_key_version: 1, text: 'Synthetic encrypted exchange',
});

function receiveContext(entry: ConversationEntry, senderId: string): import('../src/features/conversations').ConversationReceiveContext {
  if (!entry.envelope) throw new Error('Expected an encrypted entry');
  return { conversation_id: thread, message_id: entry.entry_id, sequence: entry.sequence,
    sender_user_id: senderId, sender_device_id: 1, expected_sender_key_version: 1,
    expected_recipient_key_version: 1, envelope: entry.envelope,
    recovery_target: entry.recovery_target ?? null };
}

describe('CLIP SDK relay adapter', () => {
  it('requires the history-loss acknowledgement and can register keys before any conversation exists', async () => {
    const server = new RelayHttpFixture();
    const store = inMemoryStore();
    await expect(createConversationSession(alice, thread, server.api(alice), store))
      .rejects.toBeInstanceOf(KeyRegistrationAcknowledgementRequiredError);
    expect(await store.hasIdentityKey()).toBe(false);
    expect(server.keys.size).toBe(0);
    const registration = await createConversationSession(alice, null, server.api(alice), store, { acknowledgeUnrecoverableHistoryRisk: true });
    try {
      expect(server.keys.get(alice)?.length).toBe(1);
      await expect(registration.relay.getIdentityKey(bob)).rejects.toBeInstanceOf(ConversationCryptoError);
      expect(server.entries.length).toBe(0);
    } finally { await registration.stop(); }
  }, 30_000);

  it('registers real SDK public material and exchanges encrypted messages in both directions', async () => {
    const server = new RelayHttpFixture();
    const sessions: ConversationSession[] = [];
    const aliceStore = inMemoryStore();
    try {
      const a = await createConversationSession(alice, thread, server.api(alice), aliceStore, { acknowledgeUnrecoverableHistoryRisk: true });
      sessions.push(a);
      const b = await createConversationSession(bob, thread, server.api(bob), inMemoryStore(), { acknowledgeUnrecoverableHistoryRisk: true });
      sessions.push(b);
      const originalCas = aliceStore.compareAndSetMetadata.bind(aliceStore);
      const quota = vi.spyOn(aliceStore, 'compareAndSetMetadata').mockImplementation(async (key, expected, value) => {
        if (key.startsWith('clip:history:')) throw new Error('Synthetic storage quota failure');
        return originalCas(key, expected, value);
      });
      try {
        await expect(a.sendText(message(bob))).rejects.toThrow('Local history write failed');
        expect(server.entries.length).toBe(0);
        expect(server.submitted.length).toBe(0);
      } finally { quota.mockRestore(); }
      for (const [sender, receiver, senderId, recipientId] of [[a, b, alice, bob], [b, a, bob, alice]] as const) {
        await establish(sender, server, senderId, recipientId);
        expect(await sender.crypto.resumeParticipantSession({ userId: recipientId, keyVersion: 1 })).toBe(true);
        const outgoing = message(recipientId);
        const sent = await sender.sendText(outgoing);
        const entry = server.entries.at(-1);
        if (!entry?.envelope) throw new Error('Expected committed synthetic envelope');
        expect(sent.messageId).toBe(entry.entry_id);
        if (!receiver.history || !sender.history) throw new Error('Expected local history');
        await expect(receiver.receiveText({ conversation_id: crypto.randomUUID(), message_id: entry.entry_id, sequence: entry.sequence,
          sender_user_id: senderId, sender_device_id: 1, expected_sender_key_version: 1, expected_recipient_key_version: 1,
          envelope: entry.envelope })).rejects.toThrow('Local receive conversation mismatch');
        await receiver.receiveText({ conversation_id: thread, message_id: entry.entry_id, sequence: entry.sequence,
          sender_user_id: senderId, sender_device_id: 1, expected_sender_key_version: 1, expected_recipient_key_version: 1,
          envelope: entry.envelope });
        expect((await receiver.history.read()).received.at(-1)?.text).toBe(outgoing.text);
        expect((await sender.history.read()).sent.at(-1)?.confirmation?.message_id).toBe(entry.entry_id);
        expect(server.submitted.every((body) => !body.includes(outgoing.text))).toBe(true);
      }
      expect(server.entries.length).toBe(2);
      expect(server.keys.get(alice)?.length).toBe(1);
      expect(server.keys.get(bob)?.length).toBe(1);
      expect(await a.relay.getDevices(bob)).toEqual([{ deviceId: 1, registered: true, enabled: true, linked: false }]);
      await expect(a.relay.getIdentityKey(mallory)).rejects.toBeInstanceOf(ConversationCryptoError);
      await expect(a.relay.getDevices(mallory)).rejects.toBeInstanceOf(ConversationCryptoError);
      const reservations = await Promise.all([a.relay.fetchPreKeyBundle(bob, 1), a.relay.fetchPreKeyBundle(bob, 1)]);
      expect(reservations[0].ecOneTimePreKey?.keyId !== reservations[1].ecOneTimePreKey?.keyId).toBe(true);
      const sibling = new ConversationRelay(alice, thread, server.api(alice), aliceStore);
      const simultaneous = await Promise.all([a.relay.fetchPreKeyBundle(bob, 1), sibling.fetchPreKeyBundle(bob, 1)]);
      expect(simultaneous[0].ecOneTimePreKey?.keyId !== simultaneous[1].ecOneTimePreKey?.keyId).toBe(true);
      await expect(a.relay.fetchPreKeyBundle(mallory, 1)).rejects.toBeInstanceOf(ConversationCryptoError);
    } finally { await Promise.all(sessions.map((session) => session.stop())); }
  }, 30_000);

  it('encrypts selected contact fields, retries the same ciphertext, and rejects tampering and wrong context', async () => {
    const server = new RelayHttpFixture();
    const sessions: ConversationSession[] = [];
    try {
      const a = await createConversationSession(alice, thread, server.api(alice), inMemoryStore(), { acknowledgeUnrecoverableHistoryRisk: true });
      sessions.push(a);
      const b = await createConversationSession(bob, thread, server.api(bob), inMemoryStore(), { acknowledgeUnrecoverableHistoryRisk: true });
      sessions.push(b);
      await establish(a, server, alice, bob);
      const operationId = crypto.randomUUID();
      const contacts = { email: 'synthetic@example.invalid', upi_id: 'synthetic@oktest' };
      server.loseNextMessageReply = true;
      await expect(a.sendContactShare({ conversation_id: thread, operation_id: operationId,
        recipient_user_id: bob, client_timestamp_ms: Date.now(), sender_key_version: 1,
        recipient_key_version: 1, contacts })).rejects.toThrow();
      expect(server.entries).toHaveLength(1);
      await a.relay.retrySend(operationId);
      expect(server.entries).toHaveLength(1);
      expect(new Set(server.submitted).size).toBe(1);
      expect(server.submitted[0]).not.toContain(contacts.email);
      const entry = server.entries[0];
      if (!entry?.envelope || !a.history || !b.history) throw new Error('Expected retained encrypted contact share');
      const received = await b.crypto.receiveContactShare(receiveContext(entry, alice), b.history);
      expect(received).toMatchObject({ text: JSON.stringify(contacts) });
      expect((await b.history.read()).received.at(-1)?.text).toBe(JSON.stringify(contacts));
      // The sender's device is not the recipient. Even though it created the
      // ciphertext, the SDK must not decrypt it through the receiver path.
      await expect(a.crypto.receiveContactShare(receiveContext(entry, alice), a.history)).rejects.toThrow();
    } finally { await Promise.all(sessions.map((session) => session.stop())); }
  }, 30_000);

  it('handles an undecryptable message with SDK null response when local recovery is disabled', async () => {
    const server = new RelayHttpFixture();
    const sessions: ConversationSession[] = [];
    try {
      const aliceStore = inMemoryStore();
      const a = await createConversationSession(alice, thread, server.api(alice), aliceStore,
        { acknowledgeUnrecoverableHistoryRisk: true });
      sessions.push(a);
      const bobStore = inMemoryStore();
      const b = await createConversationSession(bob, thread, server.api(bob), bobStore,
        { acknowledgeUnrecoverableHistoryRisk: true });
      sessions.push(b);
      await establish(a, server, alice, bob);
      const priming = await a.sendText(message(bob));
      const first = server.entries.at(-1);
      if (!first?.envelope || !b.history) throw new Error('Expected priming message and recipient history');
      await b.crypto.receiveText(receiveContext(first, alice), b.history);
      expect((await b.history.read()).received.some((item) => item.message_id === priming.messageId)).toBe(true);

      const outgoing = message(bob);
      const sent = await a.sendText(outgoing);
      const original = server.entries.at(-1);
      if (!original?.envelope || !a.history) throw new Error('Expected original message and sender history');
      // In-memory local stores declare no encryption and the SDK's default
      // recovery policy intentionally retains no resendable message plaintext.
      // Simulate lost recipient session state so the real SDK emits its retry
      // request, then verify the sender answers with the SDK's null control.
      expect(aliceStore.protection.atRest).toBe('none');
      expect((await aliceStore.getMessageRecord(`${bob}:1`, outgoing.client_timestamp_ms))).toBeNull();
      await bobStore.clearAllSessions();
      await expect(b.crypto.receiveText(receiveContext(original, alice), b.history)).rejects.toThrow();
      const request = server.entries.at(-1);
      if (!request) throw new Error('Expected SDK retry request');
      expect(request?.kind).toBe('protocol_control');
      expect(request?.envelope?.sdk_message_type).toBe('retry_request');
      expect(request?.envelope?.sdk_client_message_id).toMatch(/:retry-request$/);
      expect(request?.envelope?.recovery_for_entry_id).toBe(original.entry_id);
      const requestBody = JSON.parse(server.submitted.at(-1) ?? '{}') as MessageRequest;
      expect(requestBody.operation_id).not.toBe(request?.envelope?.sdk_client_message_id);

      const failedEntryId = await processProtocolControlEntry(request, alice, thread, a);
      expect(failedEntryId).toBe(original.entry_id);
      const nullResponse = server.entries.at(-1);
      if (!nullResponse) throw new Error('Expected SDK null response');
      expect(nullResponse?.kind).toBe('protocol_control');
      expect(nullResponse?.envelope?.sdk_client_message_id).toMatch(/:null$/);
      expect(nullResponse?.envelope?.recovery_for_entry_id).toBe(original.entry_id);
      const nullBody = JSON.parse(server.submitted.at(-1) ?? '{}') as MessageRequest;
      expect(nullBody.operation_id).not.toBe(nullResponse?.envelope?.sdk_client_message_id);

      const failureForNullResponse = await processProtocolControlEntry(nullResponse, bob, thread, b);
      expect(failureForNullResponse).toBeNull();
      const received = (await b.history.read()).received.filter((item) => item.message_id === original.entry_id);
      expect(received).toHaveLength(0);
      expect(sent.messageId).toBe(original.entry_id);
      expect(server.submitted.every((body) => !body.includes(outgoing.text))).toBe(true);
    } finally { await Promise.all(sessions.map((session) => session.stop())); }
  }, 60_000);

  it('retries the original prepared ciphertext after an ambiguous commit, including adapter restart', async () => {
    const server = new RelayHttpFixture();
    const store = inMemoryStore();
    const sessions: ConversationSession[] = [];
    try {
      const a = await createConversationSession(alice, thread, server.api(alice), store, { acknowledgeUnrecoverableHistoryRisk: true });
      sessions.push(a);
      sessions.push(await createConversationSession(bob, thread, server.api(bob), inMemoryStore(), { acknowledgeUnrecoverableHistoryRisk: true }));
      await establish(a, server, alice, bob);
      server.loseNextMessageReply = true;
      const outgoing = message(bob);
      await expect(a.sendText(outgoing)).rejects.toThrow();
      expect(server.entries.length).toBe(1);
      if (!a.history) throw new Error('Expected local history');
      expect((await a.history.read()).sent[0].confirmation).toBeNull();
      await expect(a.sendText(outgoing)).rejects.toThrow('Local history write failed');
      const replay = new ConversationRelay(alice, thread, server.api(alice), store, a.history);
      await replay.retrySend(outgoing.operation_id);
      expect(server.entries.length).toBe(1);
      expect(server.submitted.length >= 2).toBe(true);
      expect(new Set(server.submitted).size).toBe(1);
      expect((await a.history.read()).sent[0].confirmation?.message_id).toBe(server.entries[0].entry_id);
      await expect(new ConversationRelay(alice, crypto.randomUUID(), server.api(alice), store)
        .retrySend(outgoing.operation_id)).rejects.toBeInstanceOf(ConversationCryptoError);
      const oldPeer = server.keys.get(bob)?.at(-1);
      if (!oldPeer) throw new Error('Expected synthetic public peer bundle');
      server.keys.set(bob, [oldPeer, { ...oldPeer, key_version: 2,
        identity: { ...oldPeer.identity, x25519_public_key_base64: btoa('c'.repeat(32)) } }]);
      const posted = server.submitted.length;
      await expect(replay.retrySend(outgoing.operation_id)).rejects.toBeInstanceOf(ConversationCryptoError);
      expect(server.submitted.length).toBe(posted);
    } finally { await Promise.all(sessions.map((session) => session.stop())); }
  }, 30_000);

  it('reuses the exact public-prekey publication after a failure before commit', async () => {
    const server = new RelayHttpFixture();
    const store = inMemoryStore();
    server.failNextPublicationBeforeCommit = true;
    await expect(createConversationSession(alice, thread, server.api(alice), store, { acknowledgeUnrecoverableHistoryRisk: true }))
      .rejects.toBeInstanceOf(ConversationCryptoError);
    const resumed = await createConversationSession(alice, thread, server.api(alice), store);
    try {
      expect(server.published.length >= 2).toBe(true);
      expect(new Set(server.published).size).toBe(1);
      expect(server.keys.get(alice)?.length).toBe(1);
    } finally { await resumed.stop(); }
  }, 30_000);

  it('resumes publication with stable retry IDs and never silently replaces missing private keys', async () => {
    const server = new RelayHttpFixture();
    const store = inMemoryStore();
    server.loseNextPublicationReply = true;
    await expect(createConversationSession(alice, thread, server.api(alice), store, { acknowledgeUnrecoverableHistoryRisk: true }))
      .rejects.toBeInstanceOf(ConversationCryptoError);
    expect(server.keys.get(alice)?.length).toBe(1);
    const resumed = await createConversationSession(alice, thread, server.api(alice), store);
    try {
      expect(server.keys.get(alice)?.length).toBe(1);
      const inventory = await resumed.relay.getPreKeyInventory(alice, 1);
      expect(inventory.ecOneTimePreKeyCount > 0).toBe(true);
      expect(inventory.kemOneTimePreKeyCount > 0).toBe(true);
      expect(inventory.ecSignedPreKey?.createdAt).toBeGreaterThan(0);
      await expect(createConversationSession(alice, thread, server.api(alice), inMemoryStore(), { acknowledgeUnrecoverableHistoryRisk: true }))
        .rejects.toBeInstanceOf(ConversationKeyStateLostError);
      await expect(createConversationSession(bob, thread, server.api(bob), store, { acknowledgeUnrecoverableHistoryRisk: true }))
        .rejects.toBeInstanceOf(ConversationCryptoError);
    } finally { await resumed.stop(); }
  }, 30_000);

  it('rejects unsupported capabilities and mismatched routes before posting', async () => {
    const server = new RelayHttpFixture();
    const relay = new ConversationRelay(alice, thread, server.api(alice), inMemoryStore());
    const route: ConversationEnvelopeRoute = { ...message(bob), sender_user_id: alice,
      protocol_id: 'open-e2ee-signal', protocol_version: '13.0.0', envelope_version: 2 };
    relay.register(route);
    expect(() => relay.register({ ...route, conversation_id: crypto.randomUUID() })).toThrow(ConversationCryptoError);
    expect(() => relay.register({ ...route, recipient_user_id: mallory })).toThrow(ConversationCryptoError);
    expect(() => relay.subscribe()).toThrow(ConversationCryptoError);
    await expect(relay.clearStaleKemPreKeys()).rejects.toBeInstanceOf(ConversationCryptoError);
    await expect(relay.createGroupState()).rejects.toBeInstanceOf(ConversationCryptoError);
    await expect(relay.registerDevice(alice, { deviceId: 2 })).rejects.toBeInstanceOf(ConversationCryptoError);
    const envelope: Envelope = { senderUserId: alice, senderDeviceId: 1, targetUserId: bob, targetDeviceId: 1,
      clientMessageId: route.operation_id, ciphertext: btoa('synthetic'), messageType: 'ciphertext', deliveryClass: 'user-visible', timestamp: route.client_timestamp_ms };
    await expect(relay.send({ ...envelope, contentKind: 'receipt' })).rejects.toBeInstanceOf(ConversationCryptoError);
    await expect(relay.send({ ...envelope, senderDeviceId: 2 })).rejects.toBeInstanceOf(ConversationCryptoError);
    expect(server.entries.length).toBe(0);
  });
});
