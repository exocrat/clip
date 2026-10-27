import {
  createSignalProtocolClient,
  ProtocolAddress,
  PostQuantumPolicy,
  BraidPolicy,
  type IncomingEnvelope,
  type ReceiveOutcome,
  type SendResult,
  type DecryptedEnvelope,
  type DeliveryRecoveredEvent,
  type DefaultSignalProtocolClient,
  type SignalProtocolRelayServer,
  type PreKeyBundle,
  type PublicKey,
  type Signature,
} from '@open-e2ee/signal-protocol-sdk';
import { isUntrustedIdentityError } from '@open-e2ee/signal-protocol-sdk';
import { compositeIdentitiesEqual } from '@open-e2ee/signal-protocol-sdk/keys';
import { indexedDbStore } from '@open-e2ee/signal-protocol-sdk/local/store/web';
import type { SignalProtocolLocalStore } from '@open-e2ee/signal-protocol-sdk/local/store';
import type {
  CipherEnvelope,
  KeyBundle,
  MemberPreKeyBundle,
} from '../../../../../contracts/generated/types.gen';

export const CLIP_PROTOCOL_ID = 'open-e2ee-signal';
export const CLIP_PROTOCOL_VERSION = '13.0.0';
export const CLIP_ENVELOPE_VERSION = 2;
const LEGACY_ENVELOPE_VERSION = 1;
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

export type OwnContactValues = Partial<Record<'email' | 'phone' | 'upi_id', string>>;
export type ConversationContactShareContext = Omit<ConversationMessageContext, 'kind' | 'text'> & {
  kind: 'contact_share';
  contacts: OwnContactValues;
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
  entry_kind?: 'message' | 'contact_share';
};

/** The application relay uses this operation-id map to bind SDK sends to CLIP threads. */
export interface ConversationRouteRegistry {
  register(route: ConversationEnvelopeRoute): void;
  registerIncomingRecovery?(context: ConversationReceiveContext): Promise<void>;
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

export type SendConversationContactShare = Omit<SendConversationMessage, 'text'> & {
  contacts: OwnContactValues;
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
  recovery_target?: {
    entry_id: string;
    sequence: number;
    sender_user_id: string;
    created_at: string;
  } | null;
};

export interface ConversationHistoryStore {
  /** Persists decrypted history only in this browser profile; it is never sent to the API. */
  put(message: ReceivedConversationMessage): Promise<void>;
}

type ProtocolClient = Pick<
  DefaultSignalProtocolClient,
  | 'userId'
  | 'establishSession'
  | 'send'
  | 'processIncomingEnvelope'
  | 'completeReceive'
  | 'receiveIncomingEnvelopes'
  | 'processPendingReceives'
  | 'registerHook'
  | 'hasSession'
> & {
  acceptIdentityRotation(
    userId: string,
    identity: PreKeyBundle['identity'],
  ): Promise<unknown>;
};

type IdentityDirectory = Pick<SignalProtocolRelayServer, 'getIdentityKey'>;

export const KEY_REGISTRATION_WARNING =
  'CLIP cannot restore encryption keys. If this browser data is lost or cleared, existing chats may become permanently unreadable. A new key will not restore them.';
export const PEER_KEY_CHANGE_WARNING =
  'Accepting this key trusts CLIP’s account directory; it does not verify that the same person controls the account.';

export class ConversationCryptoError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConversationCryptoError';
  }
}

/** A newly published peer identity needs the user's deliberate acceptance. */
export class ConversationKeyChangeRequiredError extends ConversationCryptoError {
  constructor(
    readonly userId: string,
    readonly keyVersion: number,
  ) {
    super('Participant encryption identity changed; sending is blocked pending acceptance');
    this.name = 'ConversationKeyChangeRequiredError';
  }
}

/** The browser lost local protocol state while the account still has a registered key. */
export class ConversationKeyStateLostError extends ConversationCryptoError {
  constructor(readonly userId: string) {
    super('This browser no longer has the account encryption key; the server cannot restore it');
    this.name = 'ConversationKeyStateLostError';
  }
}

/** First-time registration must be preceded by an explicit history-loss acknowledgement. */
export class KeyRegistrationAcknowledgementRequiredError extends ConversationCryptoError {
  constructor() {
    super('Acknowledge the permanent-history-loss warning before creating an encryption key');
    this.name = 'KeyRegistrationAcknowledgementRequiredError';
  }
}

/** Guard automatic key creation against silent replacement after browser data loss. */
export function assertConversationKeyState(
  userId: string,
  hasLocalIdentity: boolean,
  hasDirectoryIdentity: boolean,
  acknowledgedHistoryLossRisk = false,
): void {
  if (hasLocalIdentity) return;
  if (hasDirectoryIdentity) throw new ConversationKeyStateLostError(userId);
  if (!acknowledgedHistoryLossRisk) throw new KeyRegistrationAcknowledgementRequiredError();
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

export function encodeConversationContactShare(context: ConversationContactShareContext): string {
  const contacts = context.contacts;
  const keys = Object.keys(contacts);
  if (context.version !== 1 || context.kind !== 'contact_share' || !context.conversation_id ||
    !context.sender_user_id || !context.recipient_user_id || context.sender_user_id === context.recipient_user_id ||
    !Number.isSafeInteger(context.sender_key_version) || context.sender_key_version < 1 ||
    !Number.isSafeInteger(context.recipient_key_version) || context.recipient_key_version < 1 ||
    !Number.isSafeInteger(context.client_timestamp_ms) || context.client_timestamp_ms < 0 ||
    keys.length < 1 || keys.some((key) => !['email', 'phone', 'upi_id'].includes(key)) ||
    keys.some((key) => typeof contacts[key as keyof OwnContactValues] !== 'string' ||
      !contacts[key as keyof OwnContactValues]?.trim() || (contacts[key as keyof OwnContactValues]?.length ?? 0) > 320)) {
    throw new ConversationCryptoError('Invalid contact share');
  }
  return JSON.stringify(context);
}

export function decodeConversationContactShare(
  plaintext: string,
  expected: Omit<ConversationContactShareContext, 'version' | 'kind' | 'contacts'>,
): OwnContactValues {
  let value: unknown;
  try { value = JSON.parse(plaintext); }
  catch { throw new ConversationCryptoError('Encrypted contact details have an invalid format'); }
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new ConversationCryptoError('Encrypted contact details have an unsupported format');
  }
  const item = value as Partial<ConversationContactShareContext>;
  if (item.version !== 1 || item.kind !== 'contact_share' || item.conversation_id !== expected.conversation_id ||
    item.sender_user_id !== expected.sender_user_id || item.recipient_user_id !== expected.recipient_user_id ||
    item.sender_key_version !== expected.sender_key_version || item.recipient_key_version !== expected.recipient_key_version ||
    item.client_timestamp_ms !== expected.client_timestamp_ms || !item.contacts || typeof item.contacts !== 'object' ||
    Array.isArray(item.contacts)) {
    throw new ConversationCryptoError('Encrypted contact details do not match this conversation');
  }
  const fields = item.contacts as Record<string, unknown>;
  const keys = Object.keys(fields);
  if (keys.length < 1 || keys.some((key) => !['email', 'phone', 'upi_id'].includes(key)) ||
    keys.some((key) => typeof fields[key] !== 'string' || !fields[key].trim() || fields[key].length > 320)) {
    throw new ConversationCryptoError('Encrypted contact details have invalid fields');
  }
  return { ...fields } as OwnContactValues;
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
  private readonly pendingIdentityChanges = new Map<
    string,
    { identity: PreKeyBundle['identity']; keyVersion: number }
  >();
  private readonly establishedPeerVersions = new Map<string, number>();
  private recoveryHooksInstalled = false;
  private readonly recoveryContexts = new Map<string, ConversationReceiveContext>();
  private readonly recoveredTargetIds = new Set<string>();
  private activeRecoveryHistory: ConversationHistoryStore | null = null;
  private recoveryHookError: ConversationCryptoError | null = null;

  constructor(
    private readonly client: ProtocolClient,
    private readonly routes: ConversationRouteRegistry,
    private readonly identityDirectory?: IdentityDirectory,
    private readonly localStore?: Pick<SignalProtocolLocalStore, 'getContactIdentity'>,
  ) {}

  /** Establish only from the authenticated Conversations key-directory response. */
  async establishParticipantSession(
    member: MemberPreKeyBundle,
    expected: { userId: string; keyVersion: number },
  ): Promise<void> {
    const bundle = toOpenE2eePreKeyBundle(member, expected);
    try {
      await this.client.establishSession(ProtocolAddress.create(expected.userId, 1), bundle);
    } catch (error) {
      if (!isUntrustedIdentityError(error)) throw error;
      if (error.untrustedAddress.userId !== expected.userId || error.untrustedAddress.deviceId !== 1) {
        throw error;
      }
      this.pendingIdentityChanges.set(expected.userId, {
        identity: bundle.identity,
        keyVersion: expected.keyVersion,
      });
      this.establishedPeerVersions.delete(expected.userId);
      throw new ConversationKeyChangeRequiredError(expected.userId, expected.keyVersion);
    }
    this.pendingIdentityChanges.delete(expected.userId);
    this.establishedPeerVersions.set(expected.userId, expected.keyVersion);
  }

  /**
   * Accept only the current identity from the authenticated directory, then
   * replace the SDK's pinned identity and establish a fresh session.
   */
  async acceptDirectoryKeyChange(
    member: MemberPreKeyBundle,
    expected: { userId: string; keyVersion: number },
  ): Promise<void> {
    const pending = this.pendingIdentityChanges.get(expected.userId);
    const bundle = toOpenE2eePreKeyBundle(member, expected);
    if (
      !pending ||
      pending.keyVersion !== expected.keyVersion ||
      !compositeIdentitiesEqual(pending.identity, bundle.identity)
    ) {
      throw new ConversationKeyChangeRequiredError(expected.userId, expected.keyVersion);
    }
    if (!this.identityDirectory) {
      throw new ConversationCryptoError('Current account-directory identity cannot be verified');
    }
    const currentIdentity = await this.identityDirectory.getIdentityKey(expected.userId);
    if (!currentIdentity || !compositeIdentitiesEqual(currentIdentity, bundle.identity)) {
      throw new ConversationKeyChangeRequiredError(expected.userId, expected.keyVersion);
    }
    await this.client.acceptIdentityRotation(expected.userId, currentIdentity);
    this.pendingIdentityChanges.delete(expected.userId);
    await this.client.establishSession(ProtocolAddress.create(expected.userId, 1), bundle);
    this.establishedPeerVersions.set(expected.userId, expected.keyVersion);
  }

  /** Resume a persisted SDK session only when its pinned identity still matches
   * the current account directory entry; this avoids consuming a fresh prekey
   * on every page reload and fails closed on a key change or missing session.
   */
  async resumeParticipantSession(expected: { userId: string; keyVersion: number }): Promise<boolean> {
    if (!this.identityDirectory || !this.localStore) return false;
    const address = ProtocolAddress.create(expected.userId, 1);
    if (!(await this.client.hasSession(address))) return false;
    const [current, trusted] = await Promise.all([
      this.identityDirectory.getIdentityKey(expected.userId),
      this.localStore.getContactIdentity(address),
    ]);
    if (!current) throw new ConversationCryptoError('Participant identity unavailable');
    if (!trusted) throw new ConversationCryptoError('Saved participant identity is unavailable');
    if (!compositeIdentitiesEqual(current, trusted.identity)) {
      this.pendingIdentityChanges.set(expected.userId, { identity: current, keyVersion: expected.keyVersion });
      throw new ConversationKeyChangeRequiredError(expected.userId, expected.keyVersion);
    }
    this.pendingIdentityChanges.delete(expected.userId);
    this.establishedPeerVersions.set(expected.userId, expected.keyVersion);
    return true;
  }

  async sendText(request: SendConversationMessage): Promise<SendResult> {
    if (!request.text.trim()) {
      throw new ConversationCryptoError('Message text cannot be empty');
    }
    if (
      this.pendingIdentityChanges.has(request.recipient_user_id) ||
      this.establishedPeerVersions.get(request.recipient_user_id) !== request.recipient_key_version
    ) {
      throw new ConversationCryptoError('Establish a trusted participant session before sending');
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
      entry_kind: 'message',
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

    return this.sendEncrypted(route, payload);
  }

  async sendContactShare(request: SendConversationContactShare): Promise<SendResult> {
    if (this.pendingIdentityChanges.has(request.recipient_user_id) ||
      this.establishedPeerVersions.get(request.recipient_user_id) !== request.recipient_key_version) {
      throw new ConversationCryptoError('Establish a trusted participant session before sharing contacts');
    }
    const route: ConversationEnvelopeRoute = {
      conversation_id: request.conversation_id,
      operation_id: request.operation_id,
      protocol_id: CLIP_PROTOCOL_ID,
      protocol_version: CLIP_PROTOCOL_VERSION,
      envelope_version: CLIP_ENVELOPE_VERSION,
      sender_user_id: this.client.userId,
      recipient_user_id: request.recipient_user_id,
      sender_key_version: request.sender_key_version,
      recipient_key_version: request.recipient_key_version,
      client_timestamp_ms: request.client_timestamp_ms,
      entry_kind: 'contact_share',
    };
    const payload = encodeConversationContactShare({
      version: 1,
      conversation_id: route.conversation_id,
      kind: 'contact_share',
      sender_user_id: route.sender_user_id,
      recipient_user_id: route.recipient_user_id,
      sender_key_version: route.sender_key_version,
      recipient_key_version: route.recipient_key_version,
      client_timestamp_ms: route.client_timestamp_ms,
      contacts: request.contacts,
    });
    return this.sendEncrypted(route, payload);
  }

  private async sendEncrypted(route: ConversationEnvelopeRoute, plaintext: string): Promise<SendResult> {
    this.routes.register(route);
    const result = await this.client.send(route.recipient_user_id, plaintext, {
      clientMessageId: route.operation_id,
      timestamp: route.client_timestamp_ms,
    });
    if (result.clientMessageId !== route.operation_id ||
      (result.clientTimestamp !== undefined && result.clientTimestamp !== route.client_timestamp_ms)) {
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
      ![LEGACY_ENVELOPE_VERSION, CLIP_ENVELOPE_VERSION].includes(context.envelope.envelope_version) ||
      (context.envelope.envelope_version === CLIP_ENVELOPE_VERSION &&
        typeof context.envelope.sdk_client_message_id !== 'string') ||
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
      ...(context.envelope.sdk_client_message_id === null || context.envelope.sdk_client_message_id === undefined
        ? {}
        : { clientMessageId: context.envelope.sdk_client_message_id }),
      senderUserId: context.sender_user_id,
      senderDeviceId: context.sender_device_id,
      ciphertext: context.envelope.payload_base64,
      timestamp: context.envelope.client_timestamp_ms,
      messageType: context.envelope.sdk_message_type,
    };
    if (context.envelope.envelope_version === CLIP_ENVELOPE_VERSION) {
      await this.routes.registerIncomingRecovery?.(context);
    }
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

  async receiveContactShare(
    context: ConversationReceiveContext,
    history: ConversationHistoryStore,
  ): Promise<ReceivedConversationMessage | ReceiveOutcome> {
    const currentUserId = this.client.userId;
    if (context.envelope.protocol_id !== CLIP_PROTOCOL_ID ||
      context.envelope.protocol_version !== CLIP_PROTOCOL_VERSION ||
      context.envelope.envelope_version !== CLIP_ENVELOPE_VERSION ||
      !['ciphertext', 'prekey_bundle'].includes(context.envelope.sdk_message_type) ||
      context.envelope.sender_key_version !== context.expected_sender_key_version ||
      context.envelope.recipient_key_version !== context.expected_recipient_key_version ||
      !context.envelope.sdk_client_message_id || context.envelope.recovery_for_entry_id != null) {
      throw new ConversationCryptoError('Encrypted contact-share metadata is unsupported or inconsistent');
    }
    const payload = decodeCanonicalBase64(context.envelope.payload_base64, 'Encrypted payload');
    if (atob(payload).length > MAX_CIPHERTEXT_BYTES) throw new ConversationCryptoError('Encrypted payload exceeds the supported size');
    const outcome = await this.client.processIncomingEnvelope({
      id: context.message_id,
      clientMessageId: context.envelope.sdk_client_message_id,
      senderUserId: context.sender_user_id,
      senderDeviceId: context.sender_device_id,
      ciphertext: payload,
      timestamp: context.envelope.client_timestamp_ms,
      messageType: context.envelope.sdk_message_type,
    });
    if (outcome.kind !== 'processed') return outcome;
    let contacts: OwnContactValues;
    try {
      contacts = decodeConversationContactShare(outcome.plaintext, {
        conversation_id: context.conversation_id,
        sender_user_id: context.sender_user_id,
        recipient_user_id: currentUserId,
        sender_key_version: context.expected_sender_key_version,
        recipient_key_version: context.expected_recipient_key_version,
        client_timestamp_ms: context.envelope.client_timestamp_ms,
      });
    } catch (error) {
      await this.client.completeReceive(outcome.messageId);
      throw error;
    }
    const message: ReceivedConversationMessage = {
      message_id: context.message_id,
      sequence: context.sequence,
      sender_user_id: context.sender_user_id,
      client_timestamp_ms: context.envelope.client_timestamp_ms,
      sender_key_version: context.expected_sender_key_version,
      recipient_key_version: context.expected_recipient_key_version,
      text: JSON.stringify(contacts),
    };
    await history.put(message);
    await this.client.completeReceive(outcome.messageId);
    return message;
  }

  /**
   * Handle a server-marked recovery control using the SDK's retry-family receive
   * path. Encrypted recovery content is written at the server-proven original
   * position before the SDK is allowed to finish its receive work.
   */
  async receiveProtocolEntry(
    context: ConversationReceiveContext,
    history: ConversationHistoryStore,
  ): Promise<'handled' | 'pending' | 'recovered'> {
    const envelope = context.envelope;
    if (envelope.envelope_version !== CLIP_ENVELOPE_VERSION ||
      typeof envelope.sdk_client_message_id !== 'string' || !context.recovery_target ||
      (envelope.recovery_for_entry_id !== context.recovery_target.entry_id) ||
      !['ciphertext', 'prekey_bundle', 'retry_request'].includes(envelope.sdk_message_type)) {
      throw new ConversationCryptoError('Recovery envelope metadata is incomplete or inconsistent');
    }
    this.installRecoveryHooks();
    if (!this.routes.registerIncomingRecovery) {
      throw new ConversationCryptoError('Recovery routing is unavailable');
    }
    await this.routes.registerIncomingRecovery(context);
    this.recoveryContexts.set(context.message_id, context);
    this.recoveredTargetIds.delete(context.recovery_target.entry_id);
    this.activeRecoveryHistory = history;
    this.recoveryHookError = null;
    const incoming: IncomingEnvelope = {
      id: context.message_id,
      clientMessageId: envelope.sdk_client_message_id,
      senderUserId: context.sender_user_id,
      senderDeviceId: context.sender_device_id,
      ciphertext: envelope.payload_base64,
      timestamp: envelope.client_timestamp_ms,
      messageType: envelope.sdk_message_type,
    };
    const received = await this.client.receiveIncomingEnvelopes([incoming]);
    await this.client.processPendingReceives();
    if (this.recoveryHookError) throw this.recoveryHookError;
    if (received.failedMessageIds.includes(context.message_id)) return 'pending';
    const targetId = context.recovery_target.entry_id;
    const recovered = this.recoveredTargetIds.has(targetId);
    if (received.processedMessageIds.includes(context.message_id)) {
      this.recoveryContexts.delete(context.message_id);
      this.recoveredTargetIds.delete(targetId);
      if (this.recoveryContexts.size === 0) this.activeRecoveryHistory = null;
      return recovered ? 'recovered' : 'handled';
    }
    return 'pending';
  }

  private installRecoveryHooks(): void {
    if (this.recoveryHooksInstalled) return;
    this.client.registerHook('onDeliveryRecovered', (event: DeliveryRecoveredEvent) => {
      const matches = [...this.recoveryContexts.values()].filter((item) =>
        item.recovery_target?.entry_id === event.failedEnvelopeId);
      if (matches.length > 1 || (matches.length === 1 && matches[0].sender_user_id !== event.senderUserId)) {
        this.recoveryHookError = new ConversationCryptoError('SDK recovery family does not match the server target');
        throw this.recoveryHookError;
      }
    });
    this.client.registerHook('onMessageDecrypted', async (decrypted: DecryptedEnvelope) => {
      const matches = [...this.recoveryContexts.values()].filter((item) =>
        item.message_id === decrypted.messageId || item.recovery_target?.entry_id === decrypted.messageId);
      const item = matches[0];
      const target = item?.recovery_target;
      if (matches.length !== 1 || !item || !target || !this.activeRecoveryHistory) {
        this.recoveryHookError = new ConversationCryptoError('SDK decrypted content has no unique recovery route');
        throw this.recoveryHookError;
      }
      if (decrypted.senderId !== target.sender_user_id || decrypted.senderId !== item.sender_user_id) {
        this.recoveryHookError = new ConversationCryptoError('Recovered message sender does not match the original entry');
        throw this.recoveryHookError;
      }
      try {
        const decoded = decodeConversationMessage(decrypted.content, {
          conversation_id: item.conversation_id,
          sender_user_id: target.sender_user_id,
          recipient_user_id: this.client.userId,
          sender_key_version: item.expected_sender_key_version,
          recipient_key_version: item.expected_recipient_key_version,
          client_timestamp_ms: item.envelope.client_timestamp_ms,
        });
        await this.activeRecoveryHistory.put({
          message_id: target.entry_id,
          sequence: target.sequence,
          sender_user_id: decoded.sender_user_id,
          client_timestamp_ms: decoded.client_timestamp_ms,
          sender_key_version: decoded.sender_key_version,
          recipient_key_version: decoded.recipient_key_version,
          text: decoded.text,
        });
        this.recoveredTargetIds.add(target.entry_id);
      } catch {
        this.recoveryHookError = new ConversationCryptoError('Recovered content failed context or local-history validation');
        throw this.recoveryHookError;
      }
    });
    this.recoveryHooksInstalled = true;
  }
}

/** Production constructor: SDK state is local to this browser and never backed up by CLIP. */
export async function openIndexedDbConversationCrypto(
  userId: string,
  relay: SignalProtocolRelayServer,
  routes: ConversationRouteRegistry,
  options: { acknowledgeUnrecoverableHistoryRisk?: true } = {},
): Promise<ConversationCrypto> {
  const storage = await indexedDbStore();
  const hasLocalIdentity = await storage.hasIdentityKey();
  if (!hasLocalIdentity) {
    const accountIdentity = await relay.getIdentityKey(userId);
    assertConversationKeyState(
      userId,
      false,
      accountIdentity !== null,
      options.acknowledgeUnrecoverableHistoryRisk === true,
    );
  }
  const client = await createSignalProtocolClient({
    identity: { userId },
    adapters: { storage, relay },
    protocol: {
      postQuantum: PostQuantumPolicy.Required,
      braid: BraidPolicy.Required,
      // Never retain resendable plaintext in the SDK, even if a future store
      // qualifies as protected. CLIP's approved policy has no local resend cache.
      contentRecovery: { mode: 'off' },
    },
  });
  return new ConversationCrypto(client, routes, relay, storage);
}
