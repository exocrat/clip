import { useCallback, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import {
  ConversationInbox,
  ConversationThread,
  type ConversationDisplayEntry,
  type ConversationInboxItem,
} from '../features/conversations';
import './ConversationDemo.css';

export type ConversationDemoPageProps = {
  page: 'inbox' | 'thread';
  conversationId?: string;
};

const DEMO_CONVERSATION_ID = 'demo-bicycle';
const DEMO_USER_ID = 'demo-current-user';
const DEMO_PEER_ID = 'demo-other-user';

const inboxItems: ConversationInboxItem[] = [
  {
    conversation_id: DEMO_CONVERSATION_ID,
    label: 'Demo bicycle listing · Sample buyer',
    role: 'seller',
    last_activity_at: '2026-10-23T05:00:00Z',
    unread_count: 2,
  },
  {
    conversation_id: 'demo-desk',
    label: 'Demo study desk · Sample seller',
    role: 'buyer',
    last_activity_at: '2026-10-23T04:15:00Z',
    unread_count: 0,
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

/** Loopback-only presentation fixture. It never calls or impersonates a CLIP service. */
export function ConversationDemoPage({ page, conversationId }: ConversationDemoPageProps) {
  const navigate = useNavigate();
  const activeConversation = inboxItems.find((item) => item.conversation_id === conversationId);
  const [entries, setEntries] = useState(() => sampleEntries(conversationId ?? DEMO_CONVERSATION_ID));
  const refresh = useCallback(async () => undefined, []);
  const addDemoMessage = useCallback(async (text: string) => {
    setEntries((current) => [
      ...current,
      {
        entry_id: `demo-entry-${current.length + 1}`,
        sequence: current.length + 1,
        sender_user_id: DEMO_USER_ID,
        created_at: new Date().toISOString(),
        text,
        content_deleted: false,
      },
    ]);
  }, []);

  return (
    <div className="conversation-demo">
      <aside className="conversation-demo__warning" role="note">
        <strong>Development demo · synthetic data only</strong>
        <span>
          No account, API, or encryption service is connected. Messages you type are not encrypted,
          are not sent anywhere, and disappear when this page reloads. Do not enter real messages.
        </span>
      </aside>
      {page === 'inbox' ? (
        <ConversationInbox
          conversations={inboxItems}
          onRefresh={refresh}
          onOpen={(id) => navigate(`/my/conversations/${encodeURIComponent(id)}?demo=conversations`)}
        />
      ) : !activeConversation ? (
        <div className="conversation-demo__missing">
          <p>This sample conversation is not in the demo data.</p>
          <Link to="/my/conversations?demo=conversations">Back to demo inbox</Link>
        </div>
      ) : (
        <>
          <Link className="conversation-demo__back" to="/my/conversations?demo=conversations">
            ← Demo inbox
          </Link>
          <div className="conversation-demo__thread-heading">
            <h2>{activeConversation.label}</h2>
            <span>Demo conversation</span>
          </div>
          <ConversationThread
            current_user_id={DEMO_USER_ID}
            entries={entries}
            key_state={{ kind: 'ready' }}
            last_read_sequence={1}
            presentationMode="local-demo"
            onRefresh={refresh}
            onSend={addDemoMessage}
            onRetry={async () => undefined}
            onAcknowledgeDisplayed={async () => undefined}
          />
        </>
      )}
    </div>
  );
}
