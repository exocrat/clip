import type { ConversationDisplayEntry, ConversationInboxItem } from '../features/conversations';

export const DEMO_CONVERSATION_ID = 'demo-bicycle';
export const DEMO_USER_ID = 'demo-current-user';
const DEMO_PEER_ID = 'demo-other-user';

const conversations = [
  {
    conversation_id: DEMO_CONVERSATION_ID,
    label: 'Demo bicycle listing · Sample buyer',
    role: 'seller' as const,
    last_activity_at: '2026-10-23T05:00:00Z',
  },
  {
    conversation_id: 'demo-desk',
    label: 'Demo study desk · Sample seller',
    role: 'buyer' as const,
    last_activity_at: '2026-10-23T04:15:00Z',
  },
];

function sampleEntries(conversationId: string): ConversationDisplayEntry[] {
  const subject = conversationId === 'demo-desk' ? 'demo study desk' : 'demo bicycle';
  return [
    {
      entry_id: 'demo-entry-1',
      sequence: 1,
      sender_user_id: DEMO_PEER_ID,
      created_at: '2026-10-23T04:45:00Z',
      text: `Hi! Is this ${subject} still available?`,
      content_deleted: false,
    },
    {
      entry_id: 'demo-entry-2',
      sequence: 2,
      sender_user_id: DEMO_USER_ID,
      created_at: '2026-10-23T04:48:00Z',
      text: `Yes, it is. This ${subject} message is synthetic preview content.`,
      content_deleted: false,
    },
    {
      entry_id: 'demo-entry-3',
      sequence: 3,
      sender_user_id: DEMO_PEER_ID,
      created_at: '2026-10-23T04:50:00Z',
      text: 'Great, thanks. Would tomorrow afternoon work?',
      content_deleted: false,
    },
  ];
}

type DemoThreadState = { entries: ConversationDisplayEntry[]; lastReadSequence: number };

/** In-memory-only demo data. A fresh module load starts from the sample state again. */
export function createConversationDemoState() {
  const threads = new Map<string, DemoThreadState>([
    [DEMO_CONVERSATION_ID, { entries: sampleEntries(DEMO_CONVERSATION_ID), lastReadSequence: 0 }],
    ['demo-desk', { entries: sampleEntries('demo-desk'), lastReadSequence: 3 }],
  ]);

  return {
    getEntries(conversationId: string): ConversationDisplayEntry[] {
      return [...(threads.get(conversationId)?.entries ?? [])];
    },
    getLastReadSequence(conversationId: string): number {
      return threads.get(conversationId)?.lastReadSequence ?? 0;
    },
    getInboxItems(): ConversationInboxItem[] {
      return conversations.map((conversation) => {
        const thread = threads.get(conversation.conversation_id);
        const lastEntry = thread?.entries.at(-1);
        const unreadCount = thread?.entries.filter((entry) =>
          entry.sender_user_id !== DEMO_USER_ID && entry.sequence > (thread.lastReadSequence ?? 0),
        ).length ?? 0;
        return {
          ...conversation,
          last_activity_at: lastEntry?.created_at ?? conversation.last_activity_at,
          unread_count: unreadCount,
          group_unread_count: unreadCount,
        };
      });
    },
    markDisplayed(conversationId: string, sequence: number): boolean {
      const thread = threads.get(conversationId);
      if (!thread || !Number.isSafeInteger(sequence) || sequence <= thread.lastReadSequence ||
        !thread.entries.some((entry) => entry.sequence === sequence)) return false;
      thread.lastReadSequence = sequence;
      return true;
    },
    addMessage(conversationId: string, text: string, createdAt = new Date().toISOString()): boolean {
      const thread = threads.get(conversationId);
      if (!thread) return false;
      const sequence = (thread.entries.at(-1)?.sequence ?? 0) + 1;
      thread.entries.push({
        entry_id: `demo-entry-${sequence}`,
        sequence,
        sender_user_id: DEMO_USER_ID,
        created_at: createdAt,
        text,
        content_deleted: false,
      });
      return true;
    },
  };
}

/** This singleton lives only for the current page load; nothing is persisted or sent. */
export const conversationDemoState = createConversationDemoState();
