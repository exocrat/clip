import type { SignalProtocolLocalStore } from '@open-e2ee/signal-protocol-sdk/local/store';
import type { ConversationEntry } from '../../../../../contracts/generated/types.gen';
import { ConversationCryptoError, type ConversationHistoryStore, type ReceivedConversationMessage, type SendConversationMessage } from './crypto';

type LocalStore = Pick<SignalProtocolLocalStore, 'getMetadata' | 'compareAndSetMetadata'>;
export type LocalSentMessage = { request: SendConversationMessage; confirmation: ReceivedConversationMessage | null };
export type LocalConversationHistory = { version: 1; userId: string; conversationId: string; received: ReceivedConversationMessage[]; sent: LocalSentMessage[] };
const OWNER_KEY = 'clip:conversation-store-owner:v1';
const sameMessage = (a: ReceivedConversationMessage, b: ReceivedConversationMessage) =>
  (Object.keys(a) as (keyof ReceivedConversationMessage)[]).every((key) => a[key] === b[key]) &&
  (Object.keys(b) as (keyof ReceivedConversationMessage)[]).every((key) => a[key] === b[key]);

/** Browser-only plaintext cache, never a server backup. One atomic snapshot per
 * account/thread avoids torn message/index updates across reloads or tabs. This
 * MVP rewrites the thread snapshot on writes; large-history paging is not claimed.
 * Open only after the session factory has validated the account's local keys.
 */
export class ConversationLocalHistory implements ConversationHistoryStore {
  private readonly key: string;
  constructor(readonly userId: string, readonly conversationId: string, private readonly storage: LocalStore) {
    this.key = `clip:history:v1:${userId}:${conversationId}`;
  }

  private async assertOwner() {
    if (await this.storage.getMetadata(OWNER_KEY) !== this.userId) {
      throw new ConversationCryptoError('Local history account mismatch');
    }
  }

  private decode(value: string | null): LocalConversationHistory {
    if (value === null) return { version: 1, userId: this.userId, conversationId: this.conversationId, received: [], sent: [] };
    try {
      const data = JSON.parse(value) as LocalConversationHistory;
      if (data.version !== 1 || data.userId !== this.userId || data.conversationId !== this.conversationId ||
        !Array.isArray(data.received) || !Array.isArray(data.sent)) throw new Error();
      for (const message of data.received) this.validateMessage(message);
      for (const sent of data.sent) {
        this.validateRequest(sent.request);
        if (sent.confirmation !== null) {
          this.validateMessage(sent.confirmation);
          if (sent.confirmation.sender_user_id !== this.userId || sent.confirmation.text !== sent.request.text) throw new Error();
        }
      }
      return data;
    } catch { throw new ConversationCryptoError('Local history is invalid'); }
  }

  private validateMessage(message: ReceivedConversationMessage) {
    if (!message || typeof message.message_id !== 'string' || !message.message_id ||
      typeof message.sender_user_id !== 'string' || !message.sender_user_id || typeof message.text !== 'string' ||
      !Number.isSafeInteger(message.sequence) || message.sequence < 1 ||
      !Number.isSafeInteger(message.client_timestamp_ms) || message.client_timestamp_ms < 0 ||
      !Number.isSafeInteger(message.sender_key_version) || message.sender_key_version < 1 ||
      !Number.isSafeInteger(message.recipient_key_version) || message.recipient_key_version < 1) {
      throw new ConversationCryptoError('Invalid local history message');
    }
  }

  private validateRequest(request: SendConversationMessage) {
    if (!request || request.conversation_id !== this.conversationId ||
      typeof request.operation_id !== 'string' || !request.operation_id || typeof request.text !== 'string' ||
      typeof request.recipient_user_id !== 'string' || !request.recipient_user_id || request.recipient_user_id === this.userId ||
      !Number.isSafeInteger(request.client_timestamp_ms) || request.client_timestamp_ms < 0 ||
      !Number.isSafeInteger(request.sender_key_version) || request.sender_key_version < 1 ||
      !Number.isSafeInteger(request.recipient_key_version) || request.recipient_key_version < 1) {
      throw new ConversationCryptoError('Invalid local outgoing message');
    }
  }

  /** CAS retries merge concurrent writes instead of overwriting another tab. */
  private async update(change: (snapshot: LocalConversationHistory) => void): Promise<void> {
    try {
      for (let attempt = 0; attempt < 32; attempt++) {
        await this.assertOwner();
        const before = await this.storage.getMetadata(this.key);
        const snapshot = this.decode(before);
        change(snapshot);
        if (await this.storage.compareAndSetMetadata(this.key, before, JSON.stringify(snapshot))) return;
      }
      throw new Error();
    } catch { throw new ConversationCryptoError('Local history write failed'); }
  }

  /** Returns detached local data; it neither fetches messages nor acknowledges reads. */
  async read(): Promise<LocalConversationHistory> {
    try { await this.assertOwner(); return this.decode(await this.storage.getMetadata(this.key)); }
    catch { throw new ConversationCryptoError('Local history read failed'); }
  }

  /** Called after verified decryption and before SDK receive completion. */
  async put(message: ReceivedConversationMessage): Promise<void> {
    this.validateMessage(message);
    // Snapshot caller-owned values before the first await.
    const copy = { ...message };
    await this.update((snapshot) => {
      const existing = snapshot.received.find((item) => item.message_id === copy.message_id || item.sequence === copy.sequence);
      if (existing) {
        if (!sameMessage(existing, copy)) throw new Error();
        return;
      }
      if (snapshot.sent.some((item) => item.confirmation?.sequence === copy.sequence)) throw new Error();
      snapshot.received.push(copy);
      snapshot.received.sort((a, b) => a.sequence - b.sequence);
    });
  }

  /** Persist sender plaintext BEFORE encryption. Reused operations must use the
   * relay's prepared-ciphertext retry, never call encryption again, even if the
   * previous send's outcome is unknown. No automatic plaintext resend exists.
   */
  async stageSent(request: SendConversationMessage): Promise<void> {
    this.validateRequest(request);
    const copy = { ...request };
    await this.update((snapshot) => {
      if (snapshot.sent.some((item) => item.request.operation_id === copy.operation_id)) throw new Error();
      snapshot.sent.push({ request: copy, confirmation: null });
    });
  }

  /** Bind the retained sender copy to a validated server reply. Missing staged
   * text is allowed for low-level SDK/control sends; it cannot be reconstructed.
   */
  async confirmSent(operationId: string, entry: ConversationEntry): Promise<void> {
    await this.update((snapshot) => {
      const sent = snapshot.sent.find((item) => item.request.operation_id === operationId);
      if (!sent) return;
      const request = sent.request;
      if (entry.kind !== 'message' || entry.sender_user_id !== this.userId ||
        entry.envelope?.client_timestamp_ms !== request.client_timestamp_ms ||
        entry.envelope.sender_key_version !== request.sender_key_version ||
        entry.envelope.recipient_key_version !== request.recipient_key_version) throw new Error();
      const confirmation: ReceivedConversationMessage = { message_id: entry.entry_id, sequence: entry.sequence,
        sender_user_id: this.userId, client_timestamp_ms: request.client_timestamp_ms,
        sender_key_version: request.sender_key_version, recipient_key_version: request.recipient_key_version, text: request.text };
      this.validateMessage(confirmation);
      if (sent.confirmation && !sameMessage(sent.confirmation, confirmation)) throw new Error();
      if (snapshot.received.some((item) => item.sequence === entry.sequence) || snapshot.sent.some((item) =>
        item !== sent && (item.confirmation?.sequence === entry.sequence || item.confirmation?.message_id === entry.entry_id))) throw new Error();
      sent.confirmation = confirmation;
    });
  }
}
