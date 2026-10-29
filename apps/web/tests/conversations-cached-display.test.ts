import { describe, expect, it } from 'vitest';
import { verifiedCachedMessage } from '../src/features/conversations/ConversationPages';
import type { ConversationEntry } from '../../../contracts/generated/types.gen';
const cached = { message_id: 'entry', sequence: 1, sender_user_id: 'peer', client_timestamp_ms: 10, sender_key_version: 1, recipient_key_version: 1, text: 'Synthetic verified text' };
const entry = { entry_id: 'entry', sequence: 1, sender_user_id: 'peer', kind: 'message', content_deleted: false,
  created_at: '2026-10-28T00:00:00Z', envelope: { client_timestamp_ms: 10, sender_key_version: 1, recipient_key_version: 1 } } as ConversationEntry;
describe('verified local history display', () => {
  it('restores an already consumed SDK message without attempting replay decryption', () => expect(verifiedCachedMessage(entry, [cached])).toEqual(cached));
  it('does not restore content after a server retention tombstone', () => expect(verifiedCachedMessage({ ...entry, content_deleted: true, envelope: null }, [cached])).toBeNull());
  it('rejects relabeling cached plaintext to a different author or sequence', () => {
    expect(() => verifiedCachedMessage({ ...entry, sequence: 2 }, [cached])).toThrow();
    expect(() => verifiedCachedMessage({ ...entry, sender_user_id: 'other' }, [cached])).toThrow();
  });
});
