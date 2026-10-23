import type {
  ConversationEntry,
  ConversationSummary,
  ConversationsListMineData,
  EntryPage,
  KeyBundle,
  MemberKeyBundles,
  MemberPreKeyBundle,
  MessageRequest,
  OwnPreKeyInventory,
  PageResultConversationSummary,
  PreKeyBundleRequest,
  PublicKeyBundleRequest,
  PublicKeyBundleView,
  PublicPreKeyBatchRequest,
  PublicPreKeyBatchView,
  ReadState,
} from '../../../../../contracts/generated/types.gen';

/** Identity supplies authenticated requests, including its chosen CSRF/session handling.
 * There is deliberately no default fetch or browser-supplied actor/header fallback.
 */
export type ConversationHttpTransport = (
  path: string,
  init: RequestInit,
) => Promise<Response>;

export type ConversationListQuery = NonNullable<ConversationsListMineData['query']>;

/** Content-free errors are safe to map to UI states; never retain the server body/cause. */
export class ConversationApiError extends Error {
  constructor(readonly status: number, readonly kind: 'http' | 'transport' | 'invalid_response') {
    super('Conversation request could not be completed');
    this.name = 'ConversationApiError';
  }
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
type RecordValue = Record<string, unknown>;
const record = (value: unknown): value is RecordValue =>
  typeof value === 'object' && value !== null && !Array.isArray(value);
const natural = (value: unknown): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
const positive = (value: unknown): value is number => natural(value) && value > 0;
const uuid = (value: unknown): value is string => typeof value === 'string' && UUID.test(value);
const instant = (value: unknown): boolean =>
  typeof value === 'string' && value.endsWith('Z') && Number.isFinite(Date.parse(value));

/** Validate public byte encodings, not signatures; the SDK verifies signatures itself. */
function bytes(value: unknown, size: number): boolean {
  if (typeof value !== 'string') return false;
  try {
    const decoded = atob(value);
    return decoded.length === size && btoa(decoded) === value;
  } catch {
    return false;
  }
}

function signedKey(value: unknown, size: number): boolean {
  return record(value) && natural(value.key_id) && value.key_id <= 4_294_967_295 &&
    bytes(value.public_key_base64, size) && bytes(value.signature_base64, 64);
}

function keyBundle(value: unknown): boolean {
  return record(value) && uuid(value.user_id) && positive(value.key_version) &&
    value.protocol_id === 'open-e2ee-signal' && value.protocol_version === '13.0.0' &&
    positive(value.registration_id) && value.registration_id <= 16383 && value.device_id === 1 &&
    record(value.identity) && value.identity.version === 1 &&
    bytes(value.identity.x25519_public_key_base64, 32) &&
    bytes(value.identity.ed25519_public_key_base64, 32) &&
    signedKey(value.ec_signed_prekey, 32) && signedKey(value.kem_last_resort_prekey, 1569);
}

function prekey(value: unknown, kem: boolean): boolean {
  return value === null || value === undefined || (record(value) &&
    value.key_type === (kem ? 'kemOneTimePreKey' : 'ecPreKey') && natural(value.key_id) &&
    bytes(value.public_key_base64, kem ? 1569 : 32) &&
    (kem ? bytes(value.signature_base64, 64) : value.signature_base64 == null));
}

function summary(value: unknown): boolean {
  if (!record(value)) return false;
  const offer = value.current_offer;
  return uuid(value.conversation_id) && uuid(value.origin_id) &&
    ['sale_listing', 'wanted_request'].includes(String(value.origin_kind)) &&
    uuid(value.initiator_user_id) && uuid(value.counterparty_user_id) &&
    ['initiator', 'origin_owner'].includes(String(value.caller_role)) &&
    instant(value.last_activity_at) && natural(value.own_last_read_sequence) && natural(value.unread_count) &&
    (offer == null || (record(offer) && uuid(offer.offer_id) && positive(offer.revision) &&
      natural(offer.amount_paise) && offer.amount_paise % 100 === 0 &&
      ['submitted', 'withdrawn'].includes(String(offer.status)) && instant(offer.updated_at)));
}

function entry(value: unknown): boolean {
  if (!record(value) || !uuid(value.entry_id) || !positive(value.sequence) ||
    !uuid(value.sender_user_id) || !instant(value.created_at) ||
    !['message', 'protocol_control', 'contact_share'].includes(String(value.kind)) ||
    typeof value.content_deleted !== 'boolean') return false;
  const envelope = value.envelope;
  if (value.content_deleted) return envelope == null;
  if (!record(envelope) || envelope.protocol_id !== 'open-e2ee-signal' ||
    envelope.protocol_version !== '13.0.0' || envelope.envelope_version !== 1 ||
    !natural(envelope.client_timestamp_ms) || typeof envelope.payload_base64 !== 'string') return false;
  try {
    const payload = atob(envelope.payload_base64);
    if (payload.length < 1 || payload.length > 65536 || btoa(payload) !== envelope.payload_base64) return false;
  } catch {
    return false;
  }
  return value.kind === 'protocol_control'
    ? envelope.sdk_message_type === 'retry_request' && envelope.sender_key_version === null && envelope.recipient_key_version === null
    : positive(envelope.sender_key_version) && positive(envelope.recipient_key_version) &&
      (value.kind === 'contact_share'
        ? envelope.sdk_message_type === 'ciphertext'
        : ['ciphertext', 'prekey_bundle'].includes(String(envelope.sdk_message_type)));
}

const inventory = (value: unknown): boolean => record(value) && positive(value.key_version) &&
  natural(value.ec_one_time_count) && natural(value.kem_one_time_count);

/** HTTP binding only. Crypto, polling, display/read acknowledgement and retry policy stay outside.
 * No request is retried automatically: ambiguous writes must reuse the caller's prepared request.
 */
export class ConversationApi {
  constructor(private readonly transport: ConversationHttpTransport) {}

  private async request<T>(
    path: string, method: 'GET' | 'POST' | 'PUT', validate: (value: unknown) => boolean,
    body?: unknown, signal?: AbortSignal,
  ): Promise<T> {
    let response: Response;
    try {
      response = await this.transport(path, {
        method, signal, redirect: 'error', cache: 'no-store',
        headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
    } catch {
      throw new ConversationApiError(0, 'transport');
    }
    if (!response.ok) throw new ConversationApiError(response.status, 'http');
    try {
      if (response.redirected || response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'application/json') {
        throw new Error();
      }
      const value: unknown = await response.json();
      if (!validate(value)) throw new Error();
      return value as T;
    } catch {
      throw new ConversationApiError(0, 'invalid_response');
    }
  }

  private threadPath(conversationId: string): string {
    if (!uuid(conversationId)) throw new ConversationApiError(0, 'invalid_response');
    return `/conversations/${conversationId}`;
  }

  async listMine(query: ConversationListQuery = {}, signal?: AbortSignal): Promise<PageResultConversationSummary> {
    const parameters = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null) parameters.set(key, String(value));
    }
    const suffix = parameters.size ? `?${parameters}` : '';
    return this.request(`/conversations${suffix}`, 'GET', (value) => record(value) &&
      Array.isArray(value.items) && value.items.every(summary) && positive(value.page) &&
      typeof value.page_size === 'number' && [20, 50, 100].includes(value.page_size) &&
      typeof value.has_next === 'boolean', undefined, signal);
  }

  readSummary(conversationId: string, signal?: AbortSignal): Promise<ConversationSummary> {
    return this.request(this.threadPath(conversationId), 'GET',
      (value) => summary(value) && record(value) && value.conversation_id === conversationId,
      undefined, signal);
  }

  readEntries(conversationId: string, afterSequence = 0, signal?: AbortSignal): Promise<EntryPage> {
    if (!natural(afterSequence)) throw new RangeError('Invalid entry cursor');
    return this.request(`${this.threadPath(conversationId)}/entries?after_sequence=${afterSequence}&page_size=100`, 'GET',
      (value) => record(value) && Array.isArray(value.items) && value.items.every(entry) &&
        natural(value.scanned_through_sequence) && value.scanned_through_sequence >= afterSequence &&
        typeof value.has_more === 'boolean' &&
        (!value.has_more || value.scanned_through_sequence > afterSequence) &&
        value.items.every((item, index, items) => item.sequence > afterSequence &&
          item.sequence <= Number(value.scanned_through_sequence) &&
          (index === 0 || item.sequence > items[index - 1].sequence)), undefined, signal);
  }

  submitMessage(conversationId: string, payload: MessageRequest): Promise<ConversationEntry> {
    return this.request(`${this.threadPath(conversationId)}/messages`, 'POST',
      (value) => entry(value) && record(value) && !value.content_deleted && record(value.envelope) &&
        Object.entries(payload.envelope).every(([key, expected]) =>
          record(value.envelope) && value.envelope[key] === expected), payload);
  }

  readState(conversationId: string): Promise<ReadState> {
    return this.request(`${this.threadPath(conversationId)}/read-state`, 'GET',
      (value) => record(value) && natural(value.own_last_read_sequence));
  }

  acknowledgeDisplayed(conversationId: string, sequence: number): Promise<ReadState> {
    if (!natural(sequence)) throw new RangeError('Invalid displayed sequence');
    return this.request(`${this.threadPath(conversationId)}/read-state`, 'PUT',
      (value) => record(value) && natural(value.own_last_read_sequence) && value.own_last_read_sequence >= sequence,
      { last_read_sequence: sequence });
  }

  readMemberKeys(conversationId: string): Promise<MemberKeyBundles> {
    return this.request(`${this.threadPath(conversationId)}/keys`, 'GET',
      (value) => record(value) && Array.isArray(value.members) && value.members.length >= 2 && value.members.every(keyBundle));
  }

  /** Null is an explicit never-registered account, never a fallback for HTTP failure. */
  readOwnKey(): Promise<KeyBundle | null> {
    return this.request('/me/conversation-key', 'GET',
      (value) => value === null || keyBundle(value));
  }

  registerOwnKey(payload: PublicKeyBundleRequest): Promise<PublicKeyBundleView> {
    return this.request('/me/conversation-key', 'PUT', (value) => record(value) && uuid(value.user_id) &&
      positive(value.key_version) && value.protocol_id === payload.protocol_id && value.protocol_version === payload.protocol_version, payload);
  }

  readOwnInventory(): Promise<OwnPreKeyInventory> {
    return this.request('/me/conversation-prekeys', 'GET', inventory);
  }

  publishOwnPrekeys(payload: PublicPreKeyBatchRequest): Promise<PublicPreKeyBatchView> {
    return this.request('/me/conversation-prekeys', 'POST',
      (value) => inventory(value) && record(value) && value.key_version === payload.key_version, payload);
  }

  consumeMemberPrekeys(conversationId: string, payload: PreKeyBundleRequest): Promise<MemberPreKeyBundle> {
    return this.request(`${this.threadPath(conversationId)}/prekey-bundle`, 'POST',
      (value) => record(value) && keyBundle(value.key_bundle) && record(value.key_bundle) &&
        value.registration_id === value.key_bundle.registration_id && value.device_id === 1 &&
        prekey(value.ec_one_time_prekey, false) && prekey(value.kem_one_time_prekey, true), payload);
  }
}
