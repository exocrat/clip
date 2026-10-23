import {
  BraidPolicy,
  PostQuantumPolicy,
  ProtocolAddress,
  UntrustedIdentityError,
  createSignalProtocolClient,
  type Ciphertext,
  type PreKeyBundle,
  type SendResult,
} from '@open-e2ee/signal-protocol-sdk';
import { inMemoryStore } from '@open-e2ee/signal-protocol-sdk/local/store/memory';
import {
  createCompositeIdentityV1,
  generateEcOneTimePreKeys,
  generateEcSignedPreKey,
  generateKemOneTimePreKeys,
  generateKyberLastResortPreKey,
} from '@open-e2ee/signal-protocol-sdk/keys';
import { describe, expect, it, vi } from 'vitest';
import {
  CLIP_ENVELOPE_VERSION,
  CLIP_PROTOCOL_ID,
  CLIP_PROTOCOL_VERSION,
  ConversationCrypto,
  ConversationCryptoError,
  ConversationKeyChangeRequiredError,
  ConversationKeyStateLostError,
  KeyRegistrationAcknowledgementRequiredError,
  assertConversationKeyState,
  decodeConversationMessage,
  encodeConversationMessage,
  toOpenE2eePreKeyBundle,
  type ConversationEnvelopeRoute,
  type ConversationHistoryStore,
} from '../src/features/conversations/crypto';
import type { MemberPreKeyBundle } from '../../../contracts/generated/types.gen';

const messageContext = {
  version: 1 as const,
  conversation_id: 'conversation-1',
  kind: 'message' as const,
  sender_user_id: 'alice',
  recipient_user_id: 'bob',
  sender_key_version: 3,
  recipient_key_version: 7,
  client_timestamp_ms: 1_797_000_000_000,
  text: 'encrypted hello',
};

const bytes = (length: number, fill = '\x01') => btoa(fill.repeat(length));
const memberBundle: MemberPreKeyBundle = {
  registration_id: 44,
  device_id: 1,
  key_bundle: {
    user_id: 'bob',
    protocol_id: CLIP_PROTOCOL_ID,
    protocol_version: CLIP_PROTOCOL_VERSION,
    key_version: 7,
    registration_id: 44,
    device_id: 1,
    identity: {
      version: 1,
      x25519_public_key_base64: bytes(32),
      ed25519_public_key_base64: bytes(32),
    },
    ec_signed_prekey: {
      key_id: 9,
      public_key_base64: bytes(32),
      signature_base64: bytes(64),
    },
    kem_last_resort_prekey: {
      key_id: 10,
      public_key_base64: bytes(1569),
      signature_base64: bytes(64),
    },
  },
  ec_one_time_prekey: {
    key_type: 'ecPreKey',
    key_id: 11,
    public_key_base64: bytes(32),
  },
  kem_one_time_prekey: {
    key_type: 'kemOneTimePreKey',
    key_id: 12,
    public_key_base64: bytes(1569),
    signature_base64: bytes(64),
  },
};

describe('conversation message context', () => {
  it('round-trips v1 context and checks all outer routing fields after decryption', () => {
    const encoded = encodeConversationMessage(messageContext);
    expect(
      decodeConversationMessage(encoded, {
        conversation_id: messageContext.conversation_id,
        sender_user_id: messageContext.sender_user_id,
        recipient_user_id: messageContext.recipient_user_id,
        sender_key_version: messageContext.sender_key_version,
        recipient_key_version: messageContext.recipient_key_version,
        client_timestamp_ms: messageContext.client_timestamp_ms,
      }),
    ).toEqual(messageContext);
  });

  it.each([
    ['conversation_id', { conversation_id: 'different-thread' }],
    ['sender_user_id', { sender_user_id: 'mallory' }],
    ['recipient_user_id', { recipient_user_id: 'mallory' }],
    ['sender_key_version', { sender_key_version: 4 }],
    ['recipient_key_version', { recipient_key_version: 8 }],
    ['client_timestamp_ms', { client_timestamp_ms: 1_797_000_000_001 }],
  ])('rejects tampering with %s', (_field, change) => {
    const encoded = encodeConversationMessage({ ...messageContext, ...change });
    expect(() =>
      decodeConversationMessage(encoded, {
        conversation_id: messageContext.conversation_id,
        sender_user_id: messageContext.sender_user_id,
        recipient_user_id: messageContext.recipient_user_id,
        sender_key_version: messageContext.sender_key_version,
        recipient_key_version: messageContext.recipient_key_version,
        client_timestamp_ms: messageContext.client_timestamp_ms,
      }),
    ).toThrow(ConversationCryptoError);
  });

  it('rejects malformed and unsupported payloads', () => {
    expect(() => decodeConversationMessage('{', messageContext)).toThrow(ConversationCryptoError);
    expect(() =>
      encodeConversationMessage({ ...messageContext, version: 2 as 1 }),
    ).toThrow(ConversationCryptoError);
  });
});

describe('authenticated participant key bundle', () => {
  it('maps a member-scoped directory bundle to exactly one SDK KEM prekey choice', () => {
    const sdkBundle = toOpenE2eePreKeyBundle(memberBundle, {
      userId: 'bob',
      keyVersion: 7,
    });
    expect(sdkBundle.deviceId).toBe(1);
    expect(sdkBundle.ecOneTimePreKey?.keyId).toBe(11);
    expect(sdkBundle.kemOneTimePreKey?.keyId).toBe(12);
    expect(sdkBundle.kemLastResortPreKey).toBeNull();
  });

  it.each([
    [{ userId: 'mallory', keyVersion: 7 }],
    [{ userId: 'bob', keyVersion: 8 }],
  ])('rejects a key-directory response for a different member or key version', (expected) => {
    expect(() => toOpenE2eePreKeyBundle(memberBundle, expected)).toThrow(
      ConversationCryptoError,
    );
  });

  it('uses the reusable KEM key only when the directory has no one-time KEM key', () => {
    const { kem_one_time_prekey: _kem, ...withoutOneTimeKem } = memberBundle;
    const sdkBundle = toOpenE2eePreKeyBundle(withoutOneTimeKem, {
      userId: 'bob',
      keyVersion: 7,
    });
    expect(sdkBundle.kemOneTimePreKey).toBeNull();
    expect(sdkBundle.kemLastResortPreKey?.keyId).toBe(10);
  });
});

describe('OpenE2EE adapter', () => {
  it('requires acknowledgement before first key creation and refuses silent replacement after loss', () => {
    expect(() => assertConversationKeyState('alice', true, true)).not.toThrow();
    expect(() => assertConversationKeyState('alice', false, false)).toThrow(
      KeyRegistrationAcknowledgementRequiredError,
    );
    expect(() => assertConversationKeyState('alice', false, false, true)).not.toThrow();
    expect(() => assertConversationKeyState('alice', false, true, true)).toThrow(
      ConversationKeyStateLostError,
    );
  });

  it('blocks sending until a participant session is established for the current bundle version', async () => {
    const send = vi.fn(async () => ({
      clientMessageId: 'operation-1',
      messageId: 'message-1',
      timestamp: messageContext.client_timestamp_ms,
      clientTimestamp: messageContext.client_timestamp_ms,
      recipientDeviceCount: 1,
    } satisfies SendResult));
    const client = {
      userId: 'alice',
      establishSession: vi.fn(async () => undefined),
      acceptIdentityRotation: vi.fn(),
      send,
      processIncomingEnvelope: vi.fn(),
      completeReceive: vi.fn(),
    } as unknown as ConstructorParameters<typeof ConversationCrypto>[0];
    const crypto = new ConversationCrypto(client, { register: vi.fn() });

    await expect(crypto.sendText({
      conversation_id: messageContext.conversation_id,
      operation_id: 'operation-1',
      recipient_user_id: 'bob',
      sender_key_version: 3,
      recipient_key_version: 7,
      client_timestamp_ms: messageContext.client_timestamp_ms,
      text: messageContext.text,
    })).rejects.toThrow(ConversationCryptoError);
    expect(send).not.toHaveBeenCalled();
    await crypto.establishParticipantSession(memberBundle, { userId: 'bob', keyVersion: 7 });
    await expect(crypto.sendText({
      conversation_id: messageContext.conversation_id,
      operation_id: 'operation-1',
      recipient_user_id: 'bob',
      sender_key_version: 3,
      recipient_key_version: 7,
      client_timestamp_ms: messageContext.client_timestamp_ms,
      text: messageContext.text,
    })).resolves.toMatchObject({ clientMessageId: 'operation-1' });
    expect(send).toHaveBeenCalledOnce();
  });

  it('blocks a changed identity until the current directory identity is deliberately accepted', async () => {
    const changedMember: MemberPreKeyBundle = {
      ...memberBundle,
      key_bundle: {
        ...memberBundle.key_bundle,
        key_version: 8,
        identity: {
          ...memberBundle.key_bundle.identity,
          x25519_public_key_base64: bytes(32, '\x02'),
        },
      },
    };
    const candidate = toOpenE2eePreKeyBundle(changedMember, { userId: 'bob', keyVersion: 8 });
    const establishSession = vi.fn()
      .mockRejectedValueOnce(new UntrustedIdentityError(ProtocolAddress.create('bob', 1), candidate.identity))
      .mockResolvedValue(undefined);
    const send = vi.fn(async () => ({
      clientMessageId: 'operation-1',
      messageId: 'message-1',
      timestamp: messageContext.client_timestamp_ms,
      clientTimestamp: messageContext.client_timestamp_ms,
      recipientDeviceCount: 1,
    } satisfies SendResult));
    const acceptIdentityRotation = vi.fn(async () => undefined);
    const relay = {
      getIdentityKey: vi.fn()
        .mockResolvedValueOnce({
          ...candidate.identity,
          x25519PublicKey: bytes(32, '\x03'),
        } as typeof candidate.identity)
        .mockResolvedValue(candidate.identity),
    };
    const client = {
      userId: 'alice',
      establishSession,
      acceptIdentityRotation,
      send,
      processIncomingEnvelope: vi.fn(),
      completeReceive: vi.fn(),
    } as unknown as ConstructorParameters<typeof ConversationCrypto>[0];
    const crypto = new ConversationCrypto(client, { register: vi.fn() }, relay);

    await expect(crypto.establishParticipantSession(changedMember, { userId: 'bob', keyVersion: 8 }))
      .rejects.toBeInstanceOf(ConversationKeyChangeRequiredError);
    await expect(crypto.sendText({
      conversation_id: messageContext.conversation_id,
      operation_id: 'operation-1',
      recipient_user_id: 'bob',
      sender_key_version: 3,
      recipient_key_version: 8,
      client_timestamp_ms: messageContext.client_timestamp_ms,
      text: messageContext.text,
    })).rejects.toThrow(ConversationCryptoError);
    expect(send).not.toHaveBeenCalled();

    await expect(crypto.acceptDirectoryKeyChange(changedMember, { userId: 'bob', keyVersion: 8 }))
      .rejects.toBeInstanceOf(ConversationKeyChangeRequiredError);
    expect(acceptIdentityRotation).not.toHaveBeenCalled();
    await crypto.acceptDirectoryKeyChange(changedMember, { userId: 'bob', keyVersion: 8 });
    expect(relay.getIdentityKey).toHaveBeenCalledTimes(2);
    expect(relay.getIdentityKey).toHaveBeenCalledWith('bob');
    expect(acceptIdentityRotation).toHaveBeenCalledWith('bob', candidate.identity);
    expect(establishSession).toHaveBeenCalledTimes(2);
  });

  it('uses the SDK send API with stable CLIP operation ID and timestamp before relay routing', async () => {
    const routeRegister = vi.fn<(route: ConversationEnvelopeRoute) => void>();
    const send = vi.fn(async (_recipient: string, _content: string, _options?: unknown) => ({
      clientMessageId: 'operation-1',
      messageId: 'server-message-1',
      timestamp: 1_797_000_000_010,
      clientTimestamp: messageContext.client_timestamp_ms,
      recipientDeviceCount: 1,
    } satisfies SendResult));
    const client = {
      userId: 'alice',
      establishSession: vi.fn(async () => undefined),
      acceptIdentityRotation: vi.fn(),
      send,
      processIncomingEnvelope: vi.fn(),
      completeReceive: vi.fn(),
    } as unknown as ConstructorParameters<typeof ConversationCrypto>[0];
    const crypto = new ConversationCrypto(client, { register: routeRegister });
    await crypto.establishParticipantSession(memberBundle, { userId: 'bob', keyVersion: 7 });

    await crypto.sendText({
      conversation_id: messageContext.conversation_id,
      operation_id: 'operation-1',
      recipient_user_id: 'bob',
      sender_key_version: messageContext.sender_key_version,
      recipient_key_version: messageContext.recipient_key_version,
      client_timestamp_ms: messageContext.client_timestamp_ms,
      text: messageContext.text,
    });

    expect(routeRegister).toHaveBeenCalledWith({
      conversation_id: 'conversation-1',
      operation_id: 'operation-1',
      protocol_id: CLIP_PROTOCOL_ID,
      protocol_version: CLIP_PROTOCOL_VERSION,
      envelope_version: CLIP_ENVELOPE_VERSION,
      sender_user_id: 'alice',
      recipient_user_id: 'bob',
      sender_key_version: 3,
      recipient_key_version: 7,
      client_timestamp_ms: messageContext.client_timestamp_ms,
    });
    expect(send).toHaveBeenCalledOnce();
    expect(send.mock.calls[0]?.[0]).toBe('bob');
    expect(send.mock.calls[0]?.[2]).toMatchObject({
      clientMessageId: 'operation-1',
      timestamp: messageContext.client_timestamp_ms,
    });
    const serialized = send.mock.calls[0]?.[1];
    expect(typeof serialized).toBe('string');
    expect(JSON.parse(serialized as string)).toEqual(messageContext);
  });

  it('discards locally decrypted plaintext when its conversation context mismatches', async () => {
    const processIncomingEnvelope = vi.fn(async () => ({
      kind: 'processed' as const,
      messageId: 'server-message-1',
      plaintext: encodeConversationMessage({
        ...messageContext,
        conversation_id: 'attacker-thread',
      }),
    }));
    const history: ConversationHistoryStore = { put: vi.fn(async () => undefined) };
    const client = {
      userId: 'bob',
      send: vi.fn(),
      processIncomingEnvelope,
      completeReceive: vi.fn(),
    } as unknown as ConstructorParameters<typeof ConversationCrypto>[0];
    const crypto = new ConversationCrypto(client, { register: vi.fn() });

    await expect(
      crypto.receiveText(
        {
          conversation_id: messageContext.conversation_id,
          message_id: 'server-message-1',
          sequence: 1,
          sender_user_id: 'alice',
          sender_device_id: 1,
          expected_sender_key_version: 3,
          expected_recipient_key_version: 7,
          envelope: {
            protocol_id: CLIP_PROTOCOL_ID,
            protocol_version: CLIP_PROTOCOL_VERSION,
            envelope_version: CLIP_ENVELOPE_VERSION,
            sdk_message_type: 'ciphertext',
            client_timestamp_ms: messageContext.client_timestamp_ms,
            sender_key_version: 3,
            recipient_key_version: 7,
            payload_base64: btoa('opaque sdk bytes'),
          },
        },
        history,
      ),
    ).rejects.toThrow(ConversationCryptoError);
    expect(history.put).not.toHaveBeenCalled();
    expect(client.completeReceive).toHaveBeenCalledWith('server-message-1');
  });

  it('rejects a non-canonical or oversized ciphertext envelope before decrypting', async () => {
    const processIncomingEnvelope = vi.fn();
    const client = {
      userId: 'bob',
      send: vi.fn(),
      processIncomingEnvelope,
      completeReceive: vi.fn(),
    } as unknown as ConstructorParameters<typeof ConversationCrypto>[0];
    const crypto = new ConversationCrypto(client, { register: vi.fn() });
    const history: ConversationHistoryStore = { put: vi.fn() };
    const context = {
      conversation_id: 'conversation-1',
      message_id: 'message-1',
      sequence: 1,
      sender_user_id: 'alice',
      sender_device_id: 1,
      expected_sender_key_version: 3,
      expected_recipient_key_version: 7,
      envelope: {
        protocol_id: CLIP_PROTOCOL_ID,
        protocol_version: CLIP_PROTOCOL_VERSION,
        envelope_version: CLIP_ENVELOPE_VERSION,
        sdk_message_type: 'ciphertext' as const,
        client_timestamp_ms: messageContext.client_timestamp_ms,
        sender_key_version: 3,
        recipient_key_version: 7,
        payload_base64: '%%%=',
      },
    };
    await expect(crypto.receiveText(context, history)).rejects.toThrow(ConversationCryptoError);
    expect(processIncomingEnvelope).not.toHaveBeenCalled();
  });
});

describe('OpenE2EE cryptography', () => {
  it('decrypts a two-client exchange and rejects tampered ciphertext and the wrong recipient key', async () => {
    const protocol = {
      postQuantum: PostQuantumPolicy.Required,
      braid: BraidPolicy.Required,
    } as const;
    const aliceStore = inMemoryStore();
    const bobStore = inMemoryStore();
    const malloryStore = inMemoryStore();
    const alice = await createSignalProtocolClient({
      identity: { userId: 'alice' },
      adapters: { storage: aliceStore },
      protocol,
    });
    const bob = await createSignalProtocolClient({
      identity: { userId: 'bob' },
      adapters: { storage: bobStore },
      protocol,
    });
    const mallory = await createSignalProtocolClient({
      identity: { userId: 'mallory' },
      adapters: { storage: malloryStore },
      protocol,
    });

    const identity = await bobStore.getIdentityKey();
    if (!identity) throw new Error('OpenE2EE did not provision Bob identity');
    const ecSignedPreKey = await generateEcSignedPreKey(identity, 1);
    const ecOneTimePreKey = (await generateEcOneTimePreKeys(1, 1))[0];
    const kemLastResortPreKey = await generateKyberLastResortPreKey(identity, 1);
    const kemOneTimePreKey = (await generateKemOneTimePreKeys(identity, 1, 1))[0];
    if (!ecOneTimePreKey || !kemOneTimePreKey) throw new Error('OpenE2EE prekey generation failed');
    await bobStore.storeEcSignedPreKey(ecSignedPreKey);
    await bobStore.storeEcOneTimePreKeys([ecOneTimePreKey]);
    await bobStore.storeKyberPreKey(kemLastResortPreKey);
    await bobStore.storeKemOneTimePreKeys([kemOneTimePreKey]);

    const bundle: PreKeyBundle = {
      registrationId: identity.registrationId,
      deviceId: 1,
      identity: createCompositeIdentityV1(identity),
      ecSignedPreKey: {
        keyId: ecSignedPreKey.keyId,
        publicKey: ecSignedPreKey.publicKey,
        signature: ecSignedPreKey.signature,
      },
      ecOneTimePreKey: {
        keyId: ecOneTimePreKey.keyId,
        publicKey: ecOneTimePreKey.publicKey,
      },
      kemOneTimePreKey: {
        keyId: kemOneTimePreKey.keyId,
        publicKey: kemOneTimePreKey.publicKey,
        signature: kemOneTimePreKey.signature,
      },
    };
    const bobAddress = ProtocolAddress.create('bob', 1);
    const aliceAddress = ProtocolAddress.create('alice', 1);
    await alice.establishSession(bobAddress, bundle);
    const plaintext = encodeConversationMessage(messageContext);
    const encrypted = await alice.encryptMessage(bobAddress, plaintext);
    await expect(bob.decryptMessage(aliceAddress, encrypted)).resolves.toBe(plaintext);

    const raw = atob(encrypted);
    const last = raw.charCodeAt(raw.length - 1) ^ 1;
    const altered = `${raw.slice(0, -1)}${String.fromCharCode(last)}`;
    const tampered = btoa(altered) as Ciphertext;
    await expect(bob.decryptMessage(aliceAddress, tampered)).rejects.toThrow();
    await expect(mallory.decryptMessage(aliceAddress, encrypted)).rejects.toThrow();
  });
});
