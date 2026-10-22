import {
  createSignalProtocolClient,
  ProtocolAddress,
  PostQuantumPolicy,
  BraidPolicy,
  type IncomingEnvelope,
  type ReceiveOutcome,
  type SendResult,
  type SignalProtocolClient,
  type SignalProtocolRelayServer,
  type PreKeyBundle,
  type PublicKey,
  type Signature,
} from '@open-e2ee/signal-protocol-sdk';
import { indexedDbStore } from '@open-e2ee/signal-protocol-sdk/local/store/web';
import type {
  CipherEnvelope,
  KeyBundle,
  MemberPreKeyBundle,
} from '../../../../../contracts/generated/types.gen';

export const CLIP_PROTOCOL_ID = 'open-e2ee-signal';
export const CLIP_PROTOCOL_VERSION = '13.0.0';
export const CLIP_ENVELOPE_VERSION = 1;
const MAX_CIPHERTEXT_BYTES = 64 * 1024;

export type ConversationMessageContext = {
  version: 1;
  conversation_id: string;
  kind: 'message';
  sender_user_id: string;
  recipient_user_id: string;
  sender_key_version: number;
  recipient_key_version: number;
  client_timestamp_ms: number;
  text: string;
};

export type ConversationEnvelopeRoute = {
  conversation_id: string;
  operation_id: string;
  protocol_id: typeof CLIP_PROTOCOL_ID;
  protocol_version: typeof CLIP_PROTOCOL_VERSION;
  envelope_version: typeof CLIP_ENVELOPE_VERSION;
  sender_user_id: string;
  recipient_user_id: string;
  sender_key_version: number;
  recipient_key_version: number;
  client_timestamp_ms: number;
};

/** The application relay uses this operation-id map to bind SDK sends to CLIP threads. */
export interface ConversationRouteRegistry {
  register(route: ConversationEnvelopeRoute): void;
}

export type SendConversationMessage = Omit<
  ConversationEnvelopeRoute,
  | 'protocol_id'
  | 'protocol_version'
  | 'envelope_version'
  | 'sender_user_id'
> & {
  sender_key_version: number;
  recipient_key_version: number;
  text: string;
};

export type ReceivedConversationMessage = {
  message_id: string;
  sequence: number;
  sender_user_id: string;
  client_timestamp_ms: number;
  sender_key_version: number;
  recipient_key_version: number;
  text: string;
};

export type ConversationReceiveContext = {
  conversation_id: string;
  message_id: string;
  sequence: number;
  sender_user_id: string;
  sender_device_id: number;
  expected_sender_key_version: number;
  expected_recipient_key_version: number;
  envelope: CipherEnvelope;
};

export interface ConversationHistoryStore {
  /** Persists decrypted history only in this browser profile; it is never sent to the API. */
  put(message: ReceivedConversationMessage): Promise<void>;
}

type ProtocolClient = Pick<
  SignalProtocolClient,
  'userId' | 'establishSession' | 'send' | 'processIncomingEnvelope' | 'completeReceive'
>;

export class ConversationCryptoError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConversationCryptoError';
  }
}

export function encodeConversationMessage(
  context: ConversationMessageContext,
): string {
  if (
    context.version !== 1 ||
    context.kind !== 'message' ||
    !context.conversation_id ||
    !context.sender_user_id ||
    !context.recipient_user_id ||
    !Number.isSafeInteger(context.sender_key_version) ||
    context.sender_key_version < 1 ||
    !Number.isSafeInteger(context.recipient_key_version) ||
    context.recipient_key_version < 1 ||
    !Number.isSafeInteger(context.client_timestamp_ms) ||
    context.client_timestamp_ms < 0 ||
    typeof context.text !== 'string'
  ) {
    throw new ConversationCryptoError('Invalid conversation message context');
  }
  return JSON.stringify(context);
}

export function decodeConversationMessage(
  plaintext: string,
  expected: Omit<ConversationMessageContext, 'text' | 'version' | 'kind'>,
): ConversationMessageContext {
  let value: unknown;
  try {
    value = JSON.parse(plaintext);
  } catch {
    throw new ConversationCryptoError('Decrypted message has an invalid format');
  }
  if (!isMessageContext(value)) {
    throw new ConversationCryptoError('Decrypted message has an unsupported format');
  }
  if (
    value.conversation_id !== expected.conversation_id ||
    value.sender_user_id !== expected.sender_user_id ||
    value.recipient_user_id !== expected.recipient_user_id ||
    value.sender_key_version !== expected.sender_key_version ||
    value.recipient_key_version !== expected.recipient_key_version ||
    value.client_timestamp_ms !== expected.client_timestamp_ms
  ) {
    throw new ConversationCryptoError('Decrypted message context does not match its envelope');
  }
  return value;
}

function isMessageContext(value: unknown): value is ConversationMessageContext {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<ConversationMessageContext>;
  return (
    candidate.version === 1 &&
    candidate.kind === 'message' &&
    typeof candidate.conversation_id === 'string' &&
    typeof candidate.sender_user_id === 'string' &&
    typeof candidate.recipient_user_id === 'string' &&
    Number.isSafeInteger(candidate.sender_key_version) &&
    Number.isSafeInteger(candidate.recipient_key_version) &&
    Number.isSafeInteger(candidate.client_timestamp_ms) &&
    typeof candidate.text === 'string'
  );
}

function decodeCanonicalBase64(value: string, field: string): string {
  let decoded: string;
  try {
    decoded = atob(value);
  } catch {
    throw new ConversationCryptoError(`${field} is not valid standard Base64`);
  }
  if (
    btoa(decoded) !== value ||
    !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value)
  ) {
    throw new ConversationCryptoError(`${field} is not canonical standard Base64`);
  }
  return value;
}

function strictBase64(value: string, bytes: number, field: string): string {
  const canonical = decodeCanonicalBase64(value, field);
  if (atob(canonical).length !== bytes) {
    throw new ConversationCryptoError(`${field} has an invalid byte length`);
  }
  return canonical;
}

function publicKey(value: string, bytes: number, field: string): PublicKey {
  return strictBase64(value, bytes, field) as PublicKey;
}

function signature(value: string, field: string): Signature {
  return strictBase64(value, 64, field) as Signature;
}

/** Validate the directory result and map only its public material to the SDK bundle. */
export function toOpenE2eePreKeyBundle(
  member: MemberPreKeyBundle,
  expected: { userId: string; keyVersion: number },
): PreKeyBundle {
  const bundle: KeyBundle = member.key_bundle;
  if (
    bundle.user_id !== expected.userId ||
    bundle.key_version !== expected.keyVersion ||
    bundle.protocol_id !== CLIP_PROTOCOL_ID ||
    bundle.protocol_version !== CLIP_PROTOCOL_VERSION ||
    member.registration_id !== bundle.registration_id ||
    member.device_id !== 1 ||
    bundle.device_id !== 1
  ) {
    throw new ConversationCryptoError('Participant key bundle identity or version mismatch');
  }
  const ecOneTime = member.ec_one_time_prekey;
  const kemOneTime = member.kem_one_time_prekey;
  if (ecOneTime && ecOneTime.key_type !== 'ecPreKey') {
    throw new ConversationCryptoError('Unexpected EC one-time prekey type');
  }
  if (kemOneTime && kemOneTime.key_type !== 'kemOneTimePreKey') {
    throw new ConversationCryptoError('Unexpected KEM one-time prekey type');
  }
  const kem = kemOneTime ?? bundle.kem_last_resort_prekey;
  if (!kem.signature_base64) {
    throw new ConversationCryptoError('KEM prekey signature is required');
  }

  return {
    registrationId: member.registration_id,
    deviceId: 1,
    identity: {
      version: 1,
      x25519PublicKey: publicKey(
        bundle.identity.x25519_public_key_base64,
        32,
        'X25519 identity key',
      ),
      ed25519PublicKey: publicKey(
        bundle.identity.ed25519_public_key_base64,
        32,
        'Ed25519 identity key',
      ),
    },
    ecSignedPreKey: {
      keyId: bundle.ec_signed_prekey.key_id,
      publicKey: publicKey(bundle.ec_signed_prekey.public_key_base64, 32, 'EC signed prekey'),
      signature: signature(bundle.ec_signed_prekey.signature_base64, 'EC prekey signature'),
    },
    ecOneTimePreKey: ecOneTime
      ? {
          keyId: ecOneTime.key_id,
          publicKey: publicKey(ecOneTime.public_key_base64, 32, 'EC one-time prekey'),
        }
      : null,
    kemOneTimePreKey: kemOneTime
      ? {
          keyId: kemOneTime.key_id,
          publicKey: publicKey(kemOneTime.public_key_base64, 1569, 'KEM one-time prekey'),
          signature: signature(kemOneTime.signature_base64 ?? '', 'KEM prekey signature'),
        }
      : null,
    kemLastResortPreKey: kemOneTime
      ? null
      : {
          keyId: bundle.kem_last_resort_prekey.key_id,
          publicKey: publicKey(
            bundle.kem_last_resort_prekey.public_key_base64,
            1569,
            'KEM last-resort prekey',
          ),
          signature: signature(
            bundle.kem_last_resort_prekey.signature_base64,
            'KEM last-resort prekey signature',
          ),
        },
  };
}

export class ConversationCrypto {
  constructor(
    private readonly client: ProtocolClient,
    private readonly routes: ConversationRouteRegistry,
  ) {}

  /** Establish only from the authenticated Conversations key-directory response. */
  async establishParticipantSession(
    member: MemberPreKeyBundle,
    expected: { userId: string; keyVersion: number },
  ): Promise<void> {
    const bundle = toOpenE2eePreKeyBundle(member, expected);
    await this.client.establishSession(ProtocolAddress.create(expected.userId, 1), bundle);
  }

  async sendText(request: SendConversationMessage): Promise<SendResult> {
    if (!request.text.trim()) {
      throw new ConversationCryptoError('Message text cannot be empty');
    }
    const senderId = this.client.userId;
    const route: ConversationEnvelopeRoute = {
      conversation_id: request.conversation_id,
      operation_id: request.operation_id,
      protocol_id: CLIP_PROTOCOL_ID,
      protocol_version: CLIP_PROTOCOL_VERSION,
      envelope_version: CLIP_ENVELOPE_VERSION,
      sender_user_id: senderId,
      recipient_user_id: request.recipient_user_id,
      sender_key_version: request.sender_key_version,
      recipient_key_version: request.recipient_key_version,
      client_timestamp_ms: request.client_timestamp_ms,
    };
    const payload = encodeConversationMessage({
      version: 1,
      conversation_id: route.conversation_id,
      kind: 'message',
      sender_user_id: senderId,
      recipient_user_id: route.recipient_user_id,
      sender_key_version: route.sender_key_version,
      recipient_key_version: route.recipient_key_version,
      client_timestamp_ms: route.client_timestamp_ms,
      text: request.text,
    });

    // Register before SDK send: the relay callback resolves the CLIP route by operation ID.
    this.routes.register(route);
    const result = await this.client.send(route.recipient_user_id, payload, {
      clientMessageId: route.operation_id,
      timestamp: route.client_timestamp_ms,
    });
    if (
      result.clientMessageId !== route.operation_id ||
      (result.clientTimestamp !== undefined && result.clientTimestamp !== route.client_timestamp_ms)
    ) {
      throw new ConversationCryptoError('OpenE2EE send identity differs from the CLIP operation');
    }
    return result;
  }

  async receiveText(
    context: ConversationReceiveContext,
    history: ConversationHistoryStore,
  ): Promise<ReceivedConversationMessage | ReceiveOutcome> {
    const currentUserId = this.client.userId;
    if (
      context.envelope.protocol_id !== CLIP_PROTOCOL_ID ||
      context.envelope.protocol_version !== CLIP_PROTOCOL_VERSION ||
      context.envelope.envelope_version !== CLIP_ENVELOPE_VERSION ||
      !['ciphertext', 'prekey_bundle'].includes(context.envelope.sdk_message_type) ||
      context.envelope.sender_key_version !== context.expected_sender_key_version ||
      context.envelope.recipient_key_version !== context.expected_recipient_key_version
    ) {
      throw new ConversationCryptoError('Encrypted envelope metadata is unsupported or inconsistent');
    }
    const canonicalPayload = decodeCanonicalBase64(
      context.envelope.payload_base64,
      'Encrypted payload',
    );
    if (atob(canonicalPayload).length > MAX_CIPHERTEXT_BYTES) {
      throw new ConversationCryptoError('Encrypted payload exceeds the supported size');
    }

    const incoming: IncomingEnvelope = {
      id: context.message_id,
      senderUserId: context.sender_user_id,
      senderDeviceId: context.sender_device_id,
      ciphertext: context.envelope.payload_base64,
      timestamp: context.envelope.client_timestamp_ms,
      messageType: context.envelope.sdk_message_type,
    };
    const outcome = await this.client.processIncomingEnvelope(incoming);
    if (outcome.kind !== 'processed') return outcome;

    let decoded: ConversationMessageContext;
    try {
      decoded = decodeConversationMessage(outcome.plaintext, {
        conversation_id: context.conversation_id,
        sender_user_id: context.sender_user_id,
        recipient_user_id: currentUserId,
        sender_key_version: context.expected_sender_key_version,
        recipient_key_version: context.expected_recipient_key_version,
        client_timestamp_ms: context.envelope.client_timestamp_ms,
      });
    } catch (error) {
      // Discard authenticated but misrouted content from the SDK's local receive queue.
      await this.client.completeReceive(outcome.messageId);
      throw error;
    }
    const message: ReceivedConversationMessage = {
      message_id: context.message_id,
      sequence: context.sequence,
      sender_user_id: decoded.sender_user_id,
      client_timestamp_ms: decoded.client_timestamp_ms,
      sender_key_version: decoded.sender_key_version,
      recipient_key_version: decoded.recipient_key_version,
      text: decoded.text,
    };
    await history.put(message);
    await this.client.completeReceive(outcome.messageId);
    return message;
  }
}

/** Production constructor: SDK state is local to this browser and never backed up by CLIP. */
export async function openIndexedDbConversationCrypto(
  userId: string,
  relay: SignalProtocolRelayServer,
  routes: ConversationRouteRegistry,
): Promise<ConversationCrypto> {
  const storage = await indexedDbStore();
  const client = await createSignalProtocolClient({
    identity: { userId },
    adapters: { storage, relay },
    protocol: {
      postQuantum: PostQuantumPolicy.Required,
      braid: BraidPolicy.Required,
    },
  });
  return new ConversationCrypto(client, routes);
}
