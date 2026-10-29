import {
  BraidPolicy,
  MAX_PREKEY_AGE_MS_DEFAULT,
  PostQuantumPolicy,
  createSignalProtocolClient,
  type DeviceRegistration,
  type Envelope,
  type PreKeyUpload,
  type SignalProtocolRelayServer,
} from '@open-e2ee/signal-protocol-sdk';
import { compositeIdentitiesEqual, createCompositeIdentityV1, deriveIdentityCommitment } from '@open-e2ee/signal-protocol-sdk/keys';
import type { AccountIdentityProvisioning, AccountIdentityRotation, IdentityType, PreKeyInventory, PreKeyPublicationPlan } from '@open-e2ee/signal-protocol-sdk/remote/relay/types';
import type { SignalProtocolLocalStore } from '@open-e2ee/signal-protocol-sdk/local/store';
import { openAccountConversationStore, CONVERSATION_STORE_OWNER } from './accountStore';
import type { ContactShareRequest, KeyBundle, MessageRequest, PublicKeyBundleRequest } from '../../../../../contracts/generated/types.gen';
import type { ConversationApi } from './api';
import {
  CLIP_ENVELOPE_VERSION, CLIP_PROTOCOL_ID, CLIP_PROTOCOL_VERSION,
  ConversationCrypto, ConversationCryptoError, assertConversationKeyState,
  toOpenE2eePreKeyBundle,
  type ConversationEnvelopeRoute, type ConversationRouteRegistry,
  type SendConversationMessage,
  type SendConversationContactShare,
  type ConversationReceiveContext,
} from './crypto';
import { ConversationLocalHistory } from './history';

const OWNER_KEY = CONVERSATION_STORE_OWNER;
const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const SDK_RECOVERY_ID = /^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}):(retry-request|resend|null)(?::([2-9]|[1-9][0-9]+))?$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const unsupported = async (): Promise<never> => { throw new ConversationCryptoError('Unsupported CLIP relay operation'); };

type PreparedSend = {
  conversationId: string;
  recipientUserId: string;
  recipientRegistrationId?: number;
  localKeyVersion: number;
  peerKeyVersion: number;
  sdkClientMessageId: string;
  recoveryTargetId: string | null;
  request: MessageRequest | ContactShareRequest;
  entryKind: 'message' | 'contact_share' | 'protocol_control';
};
type RecoveryFamilyRoute = {
  conversationId: string;
  peerUserId: string;
  targetEntryId: string;
  originalSdkClientMessageId: string;
};
type ReceivedMessageRoute = {
  conversationId: string;
  entryId: string;
  sequence: number;
  peerUserId: string;
  sdkClientMessageId: string;
  timestamp: number;
  senderKeyVersion: number;
  recipientKeyVersion: number;
};
type JournalRequest = { operation_id: string; [key: string]: unknown };

function sdkFamily(sdkClientMessageId: string): { root: string; kind: 'retry-request' | 'resend' | 'null' } | null {
  const match = SDK_RECOVERY_ID.exec(sdkClientMessageId);
  if (!match) return null;
  if (match[3] !== undefined && !Number.isSafeInteger(Number(match[3]))) return null;
  return { root: match[1], kind: match[2] as 'retry-request' | 'resend' | 'null' };
}

function isSdkClientMessageId(value: string): boolean {
  return value.length <= 128 && /^[\x21-\x7e]+$/.test(value) &&
    (UUID_V4.test(value) || sdkFamily(value) !== null);
}

function readRetryControl(payloadBase64: string): {
  targetEntryId: string; originalSdkClientMessageId: string; familyId: string; timestamp: number;
} {
  try {
    const decoded = atob(payloadBase64);
    if (decoded.length < 1 || decoded.length > 2048 || btoa(decoded) !== payloadBase64) throw new Error();
    const bytes = Uint8Array.from(decoded, (character) => character.charCodeAt(0));
    const value: unknown = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error();
    const request = value as Record<string, unknown>;
    if (request.v !== 1 || typeof request.failedEnvelopeId !== 'string' || !UUID.test(request.failedEnvelopeId) ||
      typeof request.retryId !== 'string' || !UUID.test(request.retryId) ||
      typeof request.failedTimestamp !== 'number' || !Number.isSafeInteger(request.failedTimestamp) || request.failedTimestamp < 0 ||
      typeof request.failedClientMessageId !== 'string' || !UUID_V4.test(request.failedClientMessageId)) throw new Error();
    return { targetEntryId: request.failedEnvelopeId, originalSdkClientMessageId: request.failedClientMessageId,
      familyId: request.retryId.toLowerCase(), timestamp: request.failedTimestamp };
  } catch {
    throw new ConversationCryptoError('SDK recovery request metadata is invalid');
  }
}

/** One authenticated account, one active SDK client, one selected conversation.
 * HTTP auth is supplied by Identity through ConversationApi. The relay advertises
 * no hosted/device-set/sealed-sender capability and never enables group traffic.
 * SDK metadata stores contain only public requests/ciphertext, never HTTP credentials.
 */
export class ConversationRelay implements SignalProtocolRelayServer, ConversationRouteRegistry {
  private readonly routes = new Map<string, ConversationEnvelopeRoute>();
  private publication: Promise<void> = Promise.resolve();
  private reservation: Promise<void> = Promise.resolve();
  // Distinct SDK clients must never coalesce session reservations. Within one
  // client, a failed fetch retries its UUID; a restarted client may reserve a
  // fresh pair, leaving an unused server reservation instead of reusing an OTP.
  private readonly reservationScope = crypto.randomUUID();
  private approvedRotationCommitment: Uint8Array | null = null;
  readonly relayConnectionState = { state: 'stopped' as const, since: Date.now() };

  constructor(
    readonly userId: string,
    readonly conversationId: string | null,
    private readonly api: ConversationApi,
    private readonly storage: SignalProtocolLocalStore,
    private readonly history?: ConversationLocalHistory,
    private readonly allowUnrecoverableKeyReplacement = false,
  ) {}

  private thread(): string {
    if (this.conversationId === null) throw new ConversationCryptoError('Select an authorized conversation first');
    return this.conversationId;
  }

  private own(userId: string, deviceId = 1, identityType: IdentityType = 'aci'): void {
    if (userId !== this.userId || deviceId !== 1 || identityType !== 'aci') {
      throw new ConversationCryptoError('Relay account or device scope mismatch');
    }
  }

  /** The HTTP transport's authenticated account must match this SDK client. */
  private async ownBundle(): Promise<KeyBundle | null> {
    const bundle = await this.api.readOwnKey();
    if (bundle && bundle.user_id !== this.userId) throw new ConversationCryptoError('Own key owner mismatch');
    return bundle;
  }

  /** Resolve the counterpart from the authorized summary, never a caller-chosen ID. */
  private async peer(userId?: string): Promise<string> {
    const summary = await this.api.readSummary(this.thread());
    const peerId = summary.counterparty_user_id;
    if (peerId === this.userId || (userId !== undefined && peerId !== userId) ||
      (summary.caller_role === 'initiator' && summary.initiator_user_id !== this.userId)) {
      throw new ConversationCryptoError('Relay participant scope mismatch');
    }
    return peerId;
  }

  private sdkBundle(bundle: KeyBundle) {
    return toOpenE2eePreKeyBundle({ key_bundle: bundle, registration_id: bundle.registration_id, device_id: 1 },
      { userId: bundle.user_id, keyVersion: bundle.key_version });
  }

  /** Keep local-state decoding diagnostics out of errors shown to the application. */
  private localJson<T>(serialized: string): T {
    try { return JSON.parse(serialized) as T; }
    catch { throw new ConversationCryptoError('Stored relay state is invalid'); }
  }

  /** Hashes select a local retry journal entry, not a cryptographic protocol or identity. */
  private async journal<T>(
    scope: string, body: Record<string, unknown>,
    submit: (request: JournalRequest) => Promise<T>, retain: boolean,
  ): Promise<T> {
    const encoded = JSON.stringify(body);
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(encoded));
    const fingerprint = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
    const key = `clip:relay:v1:${this.userId}:${scope}:${fingerprint}`;
    const existing = await this.storage.getMetadata(key);
    const candidate = JSON.stringify({ ...body, operation_id: crypto.randomUUID() });
    // Atomic metadata CAS also gives concurrent identical requests the same UUID.
    if (existing === null) await this.storage.compareAndSetMetadata(key, null, candidate);
    const serialized = await this.storage.getMetadata(key);
    if (!serialized) throw new ConversationCryptoError('Relay retry journal unavailable');
    const request = this.localJson<JournalRequest>(serialized);
    const { operation_id, ...saved } = request;
    if (!UUID_V4.test(operation_id) || JSON.stringify(saved) !== encoded) {
      throw new ConversationCryptoError('Relay retry journal mismatch');
    }
    const result = await submit(request);
    if (!retain) await this.storage.compareAndSetMetadata(key, serialized, null);
    return result;
  }

  /** First registration is staged until both reusable public prekeys are available. */
  async provisionIdentityKey(request: AccountIdentityProvisioning): Promise<void> {
    this.own(request.userId, request.deviceId, request.identityType);
    const local = await this.storage.getIdentityKey();
    if (!local || local.registrationId !== request.registrationId ||
      !compositeIdentitiesEqual(createCompositeIdentityV1(local), request.identity)) {
      throw new ConversationCryptoError('Local identity provisioning mismatch');
    }
    const published = await this.ownBundle();
    if (published && (published.registration_id !== request.registrationId ||
      !compositeIdentitiesEqual(this.sdkBundle(published).identity, request.identity)) &&
      !this.allowUnrecoverableKeyReplacement) {
      throw new ConversationCryptoError('Existing account identity cannot be replaced implicitly');
    }
  }

  /** Own lookup works before chat creation; peer lookup stays member-scoped. */
  async getIdentityKey(userId: string, identityType: IdentityType = 'aci') {
    if (identityType !== 'aci') throw new ConversationCryptoError('Unsupported identity namespace');
    if (userId === this.userId) {
      const own = await this.ownBundle();
      return own ? this.sdkBundle(own).identity : null;
    }
    await this.peer(userId);
    const members = await this.api.readMemberKeys(this.thread());
    const bundle = members.members.filter((key) => key.user_id === userId)
      .sort((a, b) => b.key_version - a.key_version)[0];
    if (!bundle) throw new ConversationCryptoError('Participant key unavailable');
    return this.sdkBundle(bundle).identity;
  }

  /** A published bundle means one queueable device, not online/presence status. */
  async getDevices(userId: string) {
    if (userId === this.userId) {
      return await this.ownBundle() ? [{ deviceId: 1, registered: true, enabled: true, linked: false }] : [];
    }
    await this.getIdentityKey(userId);
    return [{ deviceId: 1, registered: true, enabled: true, linked: false }];
  }

  async getActiveDevices(userId: string) {
    return (await this.getDevices(userId)).map(({ deviceId }) => ({ userId, deviceId }));
  }

  async registerDevice(userId: string, device: DeviceRegistration): Promise<number> {
    this.own(userId, device.deviceId ?? 1);
    // Device 1 is represented by the public bundle; CLIP has no linked-device registry.
    return 1;
  }

  /** Project server public bytes with their matching SDK-local creation times. */
  async getPreKeyInventory(userId: string, deviceId: number, identityType: IdentityType = 'aci'): Promise<PreKeyInventory> {
    this.own(userId, deviceId, identityType);
    const bundle = await this.ownBundle();
    if (!bundle) return { ecSignedPreKey: null, kemLastResortPreKey: null, ecOneTimePreKeyCount: 0, kemOneTimePreKeyCount: 0 };
    const counts = await this.api.readOwnInventory();
    if (counts.key_version !== bundle.key_version) throw new ConversationCryptoError('Key directory changed during inventory read');
    const signed = await this.storage.getEcSignedPreKey();
    const kem = await this.storage.getKyberPreKey();
    const metadata = (stored: typeof signed | typeof kem, keyId: number, publicKey: string) =>
      stored && stored.keyId === keyId && stored.publicKey === publicKey && Number.isSafeInteger(stored.timestamp)
        ? { keyId, publicKey, createdAt: stored.timestamp, expiresAt: stored.timestamp + MAX_PREKEY_AGE_MS_DEFAULT }
        : null;
    return {
      ecSignedPreKey: metadata(signed, bundle.ec_signed_prekey.key_id, bundle.ec_signed_prekey.public_key_base64),
      kemLastResortPreKey: metadata(kem, bundle.kem_last_resort_prekey.key_id, bundle.kem_last_resort_prekey.public_key_base64),
      ecOneTimePreKeyCount: counts.ec_one_time_count, kemOneTimePreKeyCount: counts.kem_one_time_count,
    };
  }

  async getEcSignedPreKeyMetadata(userId: string, deviceId: number, identityType?: IdentityType) {
    return (await this.getPreKeyInventory(userId, deviceId, identityType)).ecSignedPreKey;
  }
  async getKemLastResortPreKeyMetadata(userId: string, deviceId: number, identityType?: IdentityType) {
    return (await this.getPreKeyInventory(userId, deviceId, identityType)).kemLastResortPreKey;
  }
  async getPreKeyCount(userId: string, deviceId: number, type: 'ec' | 'kem', identityType?: IdentityType) {
    const inventory = await this.getPreKeyInventory(userId, deviceId, identityType);
    return type === 'ec' ? inventory.ecOneTimePreKeyCount : inventory.kemOneTimePreKeyCount;
  }

  private fence(operation: () => Promise<void>): Promise<void> {
    const result = this.publication.then(operation);
    this.publication = result.catch(() => undefined);
    return result;
  }

  /** Serialize public-key publication without transferring any SDK private fields. */
  async uploadPreKeys(userId: string, deviceId: number, keys: PreKeyUpload[], identityType?: IdentityType): Promise<void> {
    this.own(userId, deviceId, identityType);
    await this.fence(() => this.publish(keys));
  }

  /** Keep the SDK's inventory/plan/publication decision in one local publication turn. */
  async publishPlannedPreKeys(userId: string, deviceId: number, plan: PreKeyPublicationPlan, identityType?: IdentityType): Promise<void> {
    this.own(userId, deviceId, identityType);
    await this.fence(async () => {
      const uploads = await plan(await this.getPreKeyInventory(userId, deviceId, identityType));
      if (uploads.length) await this.publish([...uploads]);
    });
  }

  private async publish(keys: PreKeyUpload[]): Promise<void> {
    const local = await this.storage.getIdentityKey();
    if (!local) throw new ConversationCryptoError('Local identity unavailable');
    const identity = createCompositeIdentityV1(local);
    const current = await this.ownBundle();
    const identityChanged = current && (current.registration_id !== local.registrationId ||
      !compositeIdentitiesEqual(this.sdkBundle(current).identity, identity));
    const approvedCurrent = current && this.approvedRotationCommitment &&
      deriveIdentityCommitment(this.sdkBundle(current).identity).every((byte, index) => byte === this.approvedRotationCommitment?.[index]);
    if (identityChanged && (!this.allowUnrecoverableKeyReplacement || !approvedCurrent)) {
      throw new ConversationCryptoError('Existing account identity cannot be replaced implicitly');
    }
    const signed = keys.find((key) => key.type === 'ecSignedPreKey');
    const kem = keys.find((key) => key.type === 'kemLastResortPreKey');
    const publicSigned = signed?.signature ? { key_id: signed.keyId, public_key_base64: signed.publicKey, signature_base64: signed.signature } : current?.ec_signed_prekey;
    const publicKem = kem?.signature ? { key_id: kem.keyId, public_key_base64: kem.publicKey, signature_base64: kem.signature } : current?.kem_last_resort_prekey;
    if (!publicSigned || !publicKem || (signed && !signed.signature) || (kem && !kem.signature)) throw new ConversationCryptoError('Reusable public prekeys are incomplete');
    const body = {
      protocol_id: CLIP_PROTOCOL_ID, protocol_version: CLIP_PROTOCOL_VERSION,
      registration_id: local.registrationId, device_id: 1 as const,
      identity: { version: 1 as const, x25519_public_key_base64: identity.x25519PublicKey, ed25519_public_key_base64: identity.ed25519PublicKey },
      ec_signed_prekey: publicSigned,
      kem_last_resort_prekey: publicKem,
    };
    const unchanged = current && Object.entries(body).every(([key, value]) =>
      JSON.stringify(current[key as keyof KeyBundle]) === JSON.stringify(value));
    const version = unchanged ? current.key_version : (await this.journal('registration', body,
      (request) => this.api.registerOwnKey(request as PublicKeyBundleRequest), false)).key_version;
    if (identityChanged) this.approvedRotationCommitment = null;
    const prekeys = keys.filter((key) => key.type === 'ecPreKey' || key.type === 'kemOneTimePreKey').map((key) => ({
      key_type: key.type as 'ecPreKey' | 'kemOneTimePreKey', key_id: key.keyId,
      public_key_base64: key.publicKey, ...(key.signature ? { signature_base64: key.signature } : {}),
    }));
    for (let index = 0; index < prekeys.length; index += 200) {
      const batch = { key_version: version, prekeys: prekeys.slice(index, index + 200) };
      await this.journal('prekeys', batch, (request) => this.api.publishOwnPrekeys({ ...batch, operation_id: request.operation_id }), true);
    }
  }

  /** Fetches consume peer OTPs; concurrent successful calls get distinct reservations. */
  async fetchPreKeyBundle(userId: string, deviceId: number, _fetcherUserId?: string, identityType: IdentityType = 'aci') {
    if (deviceId !== 1 || identityType !== 'aci') throw new ConversationCryptoError('Unsupported peer device');
    const result = this.reservation.then(async () => {
      await this.peer(userId);
      const bundle = await this.journal(`reservation:${this.reservationScope}`, { conversation_id: this.thread() },
        (request) => this.api.consumeMemberPrekeys(this.thread(), { operation_id: request.operation_id }), false);
      return toOpenE2eePreKeyBundle(bundle, { userId, keyVersion: bundle.key_bundle.key_version });
    });
    this.reservation = result.then(() => undefined, () => undefined);
    return result;
  }

  /** Crypto registers authenticated routing before the SDK encrypts a user message. */
  register(route: ConversationEnvelopeRoute): void {
    if (route.sender_user_id !== this.userId || route.recipient_user_id === this.userId ||
      route.conversation_id !== this.conversationId || !UUID_V4.test(route.operation_id) ||
      route.protocol_id !== CLIP_PROTOCOL_ID || route.protocol_version !== CLIP_PROTOCOL_VERSION ||
      route.envelope_version !== CLIP_ENVELOPE_VERSION ||
      !Number.isSafeInteger(route.sender_key_version) || route.sender_key_version < 1 ||
      !Number.isSafeInteger(route.recipient_key_version) || route.recipient_key_version < 1 ||
      !Number.isSafeInteger(route.client_timestamp_ms) || route.client_timestamp_ms < 0 ||
      (route.entry_kind !== undefined && !['message', 'contact_share'].includes(route.entry_kind))) {
      throw new ConversationCryptoError('Message routing scope mismatch');
    }
    const previous = this.routes.get(route.operation_id);
    if (previous && JSON.stringify(previous) !== JSON.stringify(route)) throw new ConversationCryptoError('Message operation route changed');
    this.routes.set(route.operation_id, { ...route });
  }

  /** Bind SDK ciphertext to the CLIP route and durably prepare it before any post. */
  async send(envelope: Envelope) {
    if (envelope.senderUserId !== this.userId || envelope.senderDeviceId !== 1 || envelope.targetDeviceId !== 1 ||
      envelope.contentKind === 'receipt' || envelope.deliveryClass === 'ephemeral' || envelope.declaredDeviceIds !== undefined ||
      !envelope.clientMessageId || !isSdkClientMessageId(envelope.clientMessageId) ||
      !['ciphertext', 'prekey_bundle', 'retry_request'].includes(envelope.messageType)) {
      throw new ConversationCryptoError('Unsupported or misrouted SDK envelope');
    }
    await this.peer(envelope.targetUserId);
    const route = this.routes.get(envelope.clientMessageId);
    const family = sdkFamily(envelope.clientMessageId);
    const control = envelope.messageType === 'retry_request';
    let recoveryTargetId: string | null = null;
    let recoveryOriginal: PreparedSend | null = null;
    let localKeyVersion: number;
    let peerKeyVersion: number;
    if (control) {
      const parsed = readRetryControl(typeof envelope.ciphertext === 'string' ? envelope.ciphertext :
        btoa(Array.from(envelope.ciphertext, (byte) => String.fromCharCode(byte)).join('')));
      if (family?.kind !== 'retry-request' || family.root !== parsed.familyId) {
        throw new ConversationCryptoError('SDK recovery family does not match its request');
      }
      const failed = await this.readReceivedRoute(parsed.targetEntryId);
      if (!failed || failed.conversationId !== this.conversationId || failed.peerUserId !== envelope.targetUserId ||
        failed.sdkClientMessageId !== parsed.originalSdkClientMessageId || failed.timestamp !== parsed.timestamp) {
        throw new ConversationCryptoError('SDK recovery request does not match the failed incoming entry');
      }
      localKeyVersion = failed.recipientKeyVersion;
      peerKeyVersion = failed.senderKeyVersion;
      recoveryTargetId = parsed.targetEntryId;
      await this.persistRecoveryRoute(family.root, {
        conversationId: this.thread(), peerUserId: envelope.targetUserId,
        targetEntryId: parsed.targetEntryId, originalSdkClientMessageId: parsed.originalSdkClientMessageId,
      });
    } else if (family?.kind === 'resend' || family?.kind === 'null') {
      const savedFamily = await this.readRecoveryRoute(family.root);
      if (!savedFamily || savedFamily.conversationId !== this.conversationId || savedFamily.peerUserId !== envelope.targetUserId) {
        throw new ConversationCryptoError('SDK recovery response has no matching saved request');
      }
      const original = await this.readPrepared(savedFamily.originalSdkClientMessageId);
      if (!original || original.recipientUserId !== envelope.targetUserId ||
        original.sdkClientMessageId !== savedFamily.originalSdkClientMessageId ||
        original.request.envelope.client_timestamp_ms !== envelope.timestamp) {
        throw new ConversationCryptoError('SDK recovery response does not match the original send');
      }
      recoveryOriginal = original;
      localKeyVersion = original.localKeyVersion;
      peerKeyVersion = original.peerKeyVersion;
      recoveryTargetId = savedFamily.targetEntryId;
    } else if (!route || route.recipient_user_id !== envelope.targetUserId || route.client_timestamp_ms !== envelope.timestamp) {
      throw new ConversationCryptoError('SDK envelope has no matching application route');
    } else {
      localKeyVersion = route.sender_key_version;
      peerKeyVersion = route.recipient_key_version;
    }
    const isNullRecovery = family?.kind === 'null';
    const senderVersion = control || isNullRecovery ? null : family ?
      recoveryOriginal?.request.envelope.sender_key_version ?? null : route?.sender_key_version ?? null;
    const recipientVersion = control || isNullRecovery ? null : family ?
      recoveryOriginal?.request.envelope.recipient_key_version ?? null : route?.recipient_key_version ?? null;
    if (!control && !isNullRecovery && (senderVersion === null || recipientVersion === null)) {
      throw new ConversationCryptoError('SDK recovery response has no original key context');
    }
    const payload = typeof envelope.ciphertext === 'string' ? envelope.ciphertext :
      btoa(Array.from(envelope.ciphertext, (byte) => String.fromCharCode(byte)).join(''));
    const storageKey = `clip:relay:v1:${this.userId}:message:${envelope.clientMessageId}`;
    const previous = await this.storage.getMetadata(storageKey);
    const oldPrepared = previous ? this.localJson<PreparedSend>(previous) : null;
    const operationId = oldPrepared?.request.operation_id ?? (UUID_V4.test(envelope.clientMessageId)
      ? envelope.clientMessageId : crypto.randomUUID());
    const cipherEnvelope = {
      protocol_id: CLIP_PROTOCOL_ID, protocol_version: CLIP_PROTOCOL_VERSION, envelope_version: CLIP_ENVELOPE_VERSION,
      sdk_message_type: envelope.messageType as 'ciphertext' | 'prekey_bundle' | 'retry_request',
      client_timestamp_ms: envelope.timestamp, sender_key_version: senderVersion,
      recipient_key_version: recipientVersion, payload_base64: payload,
      sdk_client_message_id: envelope.clientMessageId, recovery_for_entry_id: recoveryTargetId,
    } as const;
    const entryKind = control || family !== null ? 'protocol_control' :
      route?.entry_kind === 'contact_share' ? 'contact_share' : 'message';
    if (entryKind === 'contact_share' &&
      (!['ciphertext', 'prekey_bundle'].includes(cipherEnvelope.sdk_message_type) || family !== null)) {
      throw new ConversationCryptoError('Contact share must use a fresh encrypted message');
    }
    const request: MessageRequest | ContactShareRequest = entryKind === 'contact_share'
      ? { operation_id: operationId, envelope: cipherEnvelope } as unknown as ContactShareRequest
      : { operation_id: operationId, envelope: cipherEnvelope } as unknown as MessageRequest;
    const prepared: PreparedSend = { conversationId: this.thread(), request, sdkClientMessageId: envelope.clientMessageId,
      recoveryTargetId, localKeyVersion, peerKeyVersion, entryKind,
      recipientUserId: envelope.targetUserId,
      ...(envelope.recipientRegistrationId === undefined ? {} : { recipientRegistrationId: envelope.recipientRegistrationId }),
    };
    const serialized = JSON.stringify(prepared);
    if (previous === null) await this.storage.compareAndSetMetadata(storageKey, null, serialized);
    const saved = await this.storage.getMetadata(storageKey);
    if (!saved || saved !== serialized) throw new ConversationCryptoError('Prepared ciphertext changed for a retry');
    if (oldPrepared && oldPrepared.request.envelope.payload_base64 !== payload) {
      throw new ConversationCryptoError('SDK message ID was reused with different ciphertext');
    }
    return this.post(prepared);
  }

  /** Persist server-verified routing for the SDK response before its receive pass. */
  async registerIncomingRecovery(context: ConversationReceiveContext): Promise<void> {
    const envelope = context.envelope;
    if (envelope.sdk_message_type !== 'retry_request') {
      if (context.recovery_target) return;
      if (envelope.envelope_version !== CLIP_ENVELOPE_VERSION || envelope.recovery_for_entry_id !== null ||
        typeof envelope.sdk_client_message_id !== 'string' || !UUID_V4.test(envelope.sdk_client_message_id)) {
        throw new ConversationCryptoError('Incoming application message cannot be used for SDK recovery');
      }
      const route: ReceivedMessageRoute = {
        conversationId: context.conversation_id, entryId: context.message_id, sequence: context.sequence,
        peerUserId: context.sender_user_id, sdkClientMessageId: envelope.sdk_client_message_id,
        timestamp: envelope.client_timestamp_ms, senderKeyVersion: context.expected_sender_key_version,
        recipientKeyVersion: context.expected_recipient_key_version,
      };
      const key = this.receivedRouteKey(route.entryId);
      const serialized = JSON.stringify(route);
      const existing = await this.storage.getMetadata(key);
      if (existing === null) await this.storage.compareAndSetMetadata(key, null, serialized);
      if (await this.storage.getMetadata(key) !== serialized) {
        throw new ConversationCryptoError('Incoming SDK recovery route changed');
      }
      return;
    }
    const family = sdkFamily(envelope.sdk_client_message_id ?? '');
    if (family?.kind !== 'retry-request' || !context.recovery_target ||
      context.recovery_target.sender_user_id !== this.userId ||
      context.recovery_target.entry_id !== envelope.recovery_for_entry_id) {
      throw new ConversationCryptoError('Incoming recovery request target is inconsistent');
    }
    const parsed = readRetryControl(envelope.payload_base64);
    if (parsed.familyId !== family.root || parsed.targetEntryId !== context.recovery_target.entry_id) {
      throw new ConversationCryptoError('Incoming recovery family does not match its target');
    }
    const original = await this.readPrepared(parsed.originalSdkClientMessageId);
    if (!original || original.recipientUserId !== context.sender_user_id ||
      original.conversationId !== context.conversation_id ||
      original.sdkClientMessageId !== parsed.originalSdkClientMessageId ||
      original.request.envelope.client_timestamp_ms !== parsed.timestamp) {
      throw new ConversationCryptoError('Incoming recovery request has no matching original send');
    }
    await this.persistRecoveryRoute(family.root, {
      conversationId: context.conversation_id, peerUserId: context.sender_user_id,
      targetEntryId: context.recovery_target.entry_id, originalSdkClientMessageId: parsed.originalSdkClientMessageId,
    });
  }

  private recoveryRouteKey(familyId: string): string {
    return `clip:relay:v2:${this.userId}:recovery:${this.thread()}:${familyId}`;
  }

  private receivedRouteKey(entryId: string): string {
    return `clip:relay:v2:${this.userId}:received:${this.thread()}:${entryId}`;
  }

  private async readReceivedRoute(entryId: string): Promise<ReceivedMessageRoute | null> {
    const raw = await this.storage.getMetadata(this.receivedRouteKey(entryId));
    if (raw === null) return null;
    const route = this.localJson<ReceivedMessageRoute>(raw);
    if (route.entryId !== entryId || route.conversationId !== this.conversationId ||
      !UUID.test(entryId) || !UUID_V4.test(route.sdkClientMessageId) ||
      !Number.isSafeInteger(route.sequence) || route.sequence < 1 ||
      !Number.isSafeInteger(route.timestamp) || route.timestamp < 0 ||
      !Number.isSafeInteger(route.senderKeyVersion) || route.senderKeyVersion < 1 ||
      !Number.isSafeInteger(route.recipientKeyVersion) || route.recipientKeyVersion < 1) {
      throw new ConversationCryptoError('Stored incoming SDK route is invalid');
    }
    return route;
  }

  private async persistRecoveryRoute(familyId: string, route: RecoveryFamilyRoute): Promise<void> {
    const key = this.recoveryRouteKey(familyId);
    const serialized = JSON.stringify(route);
    const existing = await this.storage.getMetadata(key);
    if (existing === null) await this.storage.compareAndSetMetadata(key, null, serialized);
    if (await this.storage.getMetadata(key) !== serialized) {
      throw new ConversationCryptoError('SDK recovery family was reused with another target');
    }
  }

  private async readRecoveryRoute(familyId: string): Promise<RecoveryFamilyRoute | null> {
    const raw = await this.storage.getMetadata(this.recoveryRouteKey(familyId));
    if (raw === null) return null;
    const route = this.localJson<RecoveryFamilyRoute>(raw);
    if (route.conversationId !== this.conversationId || !UUID.test(route.targetEntryId) ||
      !UUID_V4.test(route.originalSdkClientMessageId) || route.peerUserId === this.userId) {
      throw new ConversationCryptoError('Stored SDK recovery route is invalid');
    }
    return route;
  }

  private async readPrepared(sdkClientMessageId: string): Promise<PreparedSend | null> {
    const raw = await this.storage.getMetadata(`clip:relay:v1:${this.userId}:message:${sdkClientMessageId}`);
    if (raw === null) return null;
    const prepared = this.localJson<PreparedSend>(raw);
    const storedSdkId = prepared.sdkClientMessageId ?? prepared.request.envelope.sdk_client_message_id ??
      prepared.request.operation_id;
    const recoveryTargetId = prepared.recoveryTargetId ?? prepared.request.envelope.recovery_for_entry_id ?? null;
    if (storedSdkId !== sdkClientMessageId ||
      (prepared.request.envelope.sdk_client_message_id !== undefined &&
        prepared.request.envelope.sdk_client_message_id !== sdkClientMessageId) ||
      !UUID_V4.test(prepared.request.operation_id) ||
      (prepared.request.envelope.recovery_for_entry_id !== undefined &&
        prepared.request.envelope.recovery_for_entry_id !== recoveryTargetId)) {
      throw new ConversationCryptoError('Stored SDK send mapping is invalid');
    }
    const localKeyVersion = prepared.localKeyVersion ?? prepared.request.envelope.sender_key_version;
    const peerKeyVersion = prepared.peerKeyVersion ?? prepared.request.envelope.recipient_key_version;
    if (!Number.isSafeInteger(localKeyVersion) || localKeyVersion < 1 ||
      !Number.isSafeInteger(peerKeyVersion) || peerKeyVersion < 1) {
      throw new ConversationCryptoError('Stored SDK key context is invalid');
    }
    return { ...prepared, sdkClientMessageId: storedSdkId, recoveryTargetId, localKeyVersion, peerKeyVersion };
  }

  private async post(prepared: PreparedSend) {
    // Historical versions are usable only while their identity still agrees
    // with the directory. Apply the same check on a prepared retry. This is
    // not an advertised atomic server device-set/registration comparison.
    await this.peer(prepared.recipientUserId);
    const members = (await this.api.readMemberKeys(this.thread())).members;
    const current = (userId: string) => members.filter((key) => key.user_id === userId)
      .sort((a, b) => b.key_version - a.key_version)[0];
    const recipient = current(prepared.recipientUserId);
    if (!recipient || (prepared.recipientRegistrationId !== undefined &&
      prepared.recipientRegistrationId !== recipient.registration_id)) {
      throw new ConversationCryptoError('Participant registration changed');
    }
    for (const [userId, version] of [[this.userId, prepared.localKeyVersion],
      [prepared.recipientUserId, prepared.peerKeyVersion]] as const) {
      const expected = members.find((key) => key.user_id === userId && key.key_version === version);
      const latest = current(userId);
      if (!expected || !latest || !compositeIdentitiesEqual(this.sdkBundle(expected).identity, this.sdkBundle(latest).identity)) {
        throw new ConversationCryptoError('Participant identity changed; refresh key verification');
      }
    }
    const entryKind = prepared.entryKind ?? 'message';
    const result = entryKind === 'contact_share'
      ? await this.api.submitContactShare(prepared.conversationId, prepared.request as ContactShareRequest)
      : await this.api.submitMessage(prepared.conversationId, prepared.request as MessageRequest);
    if (result.sender_user_id !== this.userId || result.kind !== entryKind) {
      throw new ConversationCryptoError('Committed conversation entry does not match its request');
    }
    if (entryKind === 'message') await this.history?.confirmSent(prepared.request.operation_id, result);
    return { messageId: result.entry_id, serverTimestamp: Date.parse(result.created_at) };
  }

  /** Retry posts the already prepared bytes; it never calls SDK encryption again. */
  async retrySend(operationId: string) {
    if (!UUID_V4.test(operationId)) throw new ConversationCryptoError('Invalid retry operation');
    const saved = await this.storage.getMetadata(`clip:relay:v1:${this.userId}:message:${operationId}`);
    if (!saved) throw new ConversationCryptoError('Prepared retry unavailable');
    const prepared = this.localJson<PreparedSend>(saved);
    if (prepared.conversationId !== this.conversationId || prepared.request.operation_id !== operationId) {
      throw new ConversationCryptoError('Prepared retry routing mismatch');
    }
    return this.post(prepared);
  }

  // Polling reads retained entries; SDK delivery completion is not a read receipt
  // and must not mutate CLIP's watermark or delete retained server content.
  async markDelivered(_envelopeId: string): Promise<void> {}
  subscribe(): never { throw new ConversationCryptoError('Use CLIP entry polling instead of relay subscriptions'); }
  subscribeRelayConnectionState() { return () => undefined; }
  removeDevice = unsupported;
  clearStaleKemPreKeys = unsupported;
  createGroupState = unsupported;
  getGroupState = unsupported;
  getGroupJoinInfo = unsupported;
  getGroupChanges = unsupported;
  submitGroupChange = unsupported;
  issueAuthCredential = unsupported;

  /** Stage a user-approved identity change; publication replaces the complete
   * signed bundle in one authenticated API operation once the SDK has generated it.
   */
  async rotateIdentityKey(request: AccountIdentityRotation): Promise<void> {
    this.own(request.userId, request.deviceId, request.identityType);
    if (!this.allowUnrecoverableKeyReplacement) throw new ConversationCryptoError('Key replacement was not approved');
    const local = await this.storage.getIdentityKey();
    const current = await this.ownBundle();
    if (!local || !current || local.registrationId !== request.registrationId ||
      !compositeIdentitiesEqual(createCompositeIdentityV1(local), request.identity) ||
      !deriveIdentityCommitment(this.sdkBundle(current).identity).every((byte, index) => byte === request.expectedCurrentCommitment[index])) {
      throw new ConversationCryptoError('Account encryption key changed; refresh setup before replacing it');
    }
    this.approvedRotationCommitment = request.expectedCurrentCommitment.slice();
  }
}

export type ConversationSession = {
  crypto: ConversationCrypto;
  relay: ConversationRelay;
  history: ConversationLocalHistory | null;
  sendText: (request: SendConversationMessage) => ReturnType<ConversationCrypto['sendText']>;
  sendContactShare: (request: SendConversationContactShare) => ReturnType<ConversationCrypto['sendContactShare']>;
  receiveText: (context: ConversationReceiveContext) => ReturnType<ConversationCrypto['receiveText']>;
  stop: () => Promise<void>;
};

/** Compose real SDK crypto with a supplied platform store and authenticated API.
 * The atomic owner marker prevents a different signed-in account reusing browser keys.
 * Existing unbound keys may be adopted only when the account directory confirms them.
 */
export async function createConversationSession(
  userId: string, conversationId: string | null, api: ConversationApi, storage: SignalProtocolLocalStore,
  options: { acknowledgeUnrecoverableHistoryRisk?: true; allowUnrecoverableKeyReplacement?: true } = {},
): Promise<ConversationSession> {
  const published = await api.readOwnKey();
  if (published && published.user_id !== userId) throw new ConversationCryptoError('Own key owner mismatch');
  const local = await storage.getIdentityKey();
  const owner = await storage.getMetadata(OWNER_KEY);
  if (owner !== null && owner !== userId) throw new ConversationCryptoError('Browser keys belong to a different account');
  assertConversationKeyState(userId, local !== null, published !== null,
    options.acknowledgeUnrecoverableHistoryRisk === true, options.allowUnrecoverableKeyReplacement === true);
  const localIdentityChanged = local && published && (local.registrationId !== published.registration_id || !compositeIdentitiesEqual(createCompositeIdentityV1(local),
    toOpenE2eePreKeyBundle({ key_bundle: published, registration_id: published.registration_id, device_id: 1 },
      { userId, keyVersion: published.key_version }).identity));
  if (localIdentityChanged && !options.allowUnrecoverableKeyReplacement) {
    throw new ConversationCryptoError('Local identity differs from the account directory');
  }
  if (owner === null) {
    if (local && !published) throw new ConversationCryptoError('Unbound browser identity cannot be assigned to an account');
    await storage.compareAndSetMetadata(OWNER_KEY, null, userId);
    if (await storage.getMetadata(OWNER_KEY) !== userId) throw new ConversationCryptoError('Browser account binding changed');
  }
  const history = conversationId === null ? null : new ConversationLocalHistory(userId, conversationId, storage);
  const relay = new ConversationRelay(userId, conversationId, api, storage, history ?? undefined,
    options.allowUnrecoverableKeyReplacement === true);
  const client = await createSignalProtocolClient({
    identity: { userId, deviceId: 1 }, adapters: { storage, relay },
    protocol: { postQuantum: PostQuantumPolicy.Required, braid: BraidPolicy.Required, contentRecovery: { mode: 'off' } },
    logger: {}, deliveryReceipts: 'off',
  });
  const generatedIdentity = options.allowUnrecoverableKeyReplacement && published
    ? await storage.getIdentityKey() : null;
  const generatedIdentityChanged = generatedIdentity && published &&
    (generatedIdentity.registrationId !== published.registration_id || !compositeIdentitiesEqual(
      createCompositeIdentityV1(generatedIdentity),
      toOpenE2eePreKeyBundle({ key_bundle: published, registration_id: published.registration_id, device_id: 1 },
        { userId, keyVersion: published.key_version }).identity));
  if (client.syncStatus === 'failed' && options.allowUnrecoverableKeyReplacement && published && generatedIdentityChanged) {
    await client.rotateAccountIdentity(deriveIdentityCommitment(toOpenE2eePreKeyBundle(
      { key_bundle: published, registration_id: published.registration_id, device_id: 1 },
      { userId, keyVersion: published.key_version }).identity));
  }
  if (client.syncStatus !== 'synced') {
    await client.stop();
    throw new ConversationCryptoError('Encryption key publication did not complete');
  }
  const conversationCrypto = new ConversationCrypto(client, relay, relay, storage);
  return { relay, crypto: conversationCrypto, history,
    // The application entry point retains sender text before SDK encryption.
    // A failed/unknown attempt must retry relay.retrySend with the same UUID.
    sendText: async (request) => {
      if (!history) throw new ConversationCryptoError('Select an authorized conversation first');
      const copy = { ...request };
      await history.stageSent(copy);
      return conversationCrypto.sendText(copy);
    },
    sendContactShare: (request) => conversationCrypto.sendContactShare({
      ...request,
      contacts: { ...request.contacts },
    }),
    // A thread-bound cache cannot accept a verified message for a different thread.
    receiveText: async (context) => {
      if (!history || context.conversation_id !== history.conversationId) {
        throw new ConversationCryptoError('Local receive conversation mismatch');
      }
      return conversationCrypto.receiveText(context, history);
    },
    stop: () => client.stop() };
}

/** Browser entry point; no additional service or crypto setup is required. */
export async function openIndexedDbConversationSession(
  userId: string, conversationId: string | null, api: ConversationApi,
  options: { acknowledgeUnrecoverableHistoryRisk?: true; allowUnrecoverableKeyReplacement?: true } = {},
): Promise<ConversationSession> {
  const storage = await openAccountConversationStore(userId);
  try {
    const session = await createConversationSession(userId, conversationId, api, storage, options);
    return { ...session, stop: async () => { try { await session.stop(); } finally { storage.close(); } } };
  } catch (error) {
    storage.close();
    throw error;
  }
}
