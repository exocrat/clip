import { indexedDbStore, IndexedDbSignalProtocolStore } from '@open-e2ee/signal-protocol-sdk/local/store/web';
import { ConversationCryptoError } from './crypto';

export const CONVERSATION_STORE_OWNER = 'clip:conversation-store-owner:v1';

/** SDK13.0.0 exposes its IndexedDB adapter but has no database-name option.
 * Configure its two instance fields before initialization, with a fail-closed
 * compatibility check. Never modify shared globals or a live database. The real
 * browser regression must pass when upgrading this pinned SDK. Namespaces prevent
 * accidental account reuse; they do not protect against same-origin malicious JS.
 */
export async function openAccountConversationStore(userId: string) {
  if (!/^[0-9a-f-]{36}$/i.test(userId)) throw new ConversationCryptoError('Invalid storage account');
  const legacy = await indexedDbStore();
  const owner = await legacy.getMetadata(CONVERSATION_STORE_OWNER);
  const identity = await legacy.getIdentityKey();
  // Preserve existing keys/history. An unbound legacy identity is still checked
  // against the authenticated directory by createConversationSession before use.
  if (owner === userId || (owner === null && identity !== null)) return legacy;
  legacy.close();
  const store = new IndexedDbSignalProtocolStore();
  const database = Object.getOwnPropertyDescriptor(store, 'dbName');
  const locks = Object.getOwnPropertyDescriptor(store, 'storeIdentity');
  if (!database || !locks || database.value !== 'signal-protocol-storage' || locks.value !== database.value ||
    !database.writable || !locks.writable) throw new ConversationCryptoError('Unsupported browser storage adapter');
  const namespace = `clip-conversations-v1-${userId.toLowerCase()}`;
  Object.defineProperty(store, 'dbName', { ...database, value: namespace });
  Object.defineProperty(store, 'storeIdentity', { ...locks, value: namespace });
  await store.initialize();
  return store;
}
