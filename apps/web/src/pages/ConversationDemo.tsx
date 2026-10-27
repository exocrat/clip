import { useCallback, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { ConversationInbox, ConversationThread } from '../features/conversations';
import { conversationDemoState, DEMO_CONVERSATION_ID, DEMO_USER_ID } from './conversationDemoState';
import './ConversationDemo.css';

export type ConversationDemoPageProps = {
  page: 'inbox' | 'thread';
  conversationId?: string;
};

/** Loopback-only presentation fixture. It never calls or impersonates a CLIP service. */
export function ConversationDemoPage({ page, conversationId }: ConversationDemoPageProps) {
  const navigate = useNavigate();
  const activeConversation = conversationDemoState.getInboxItems().find((item) => item.conversation_id === conversationId);
  const [, setRenderVersion] = useState(0);
  const activeId = conversationId ?? DEMO_CONVERSATION_ID;
  const entries = conversationDemoState.getEntries(activeId);
  const refresh = useCallback(async () => undefined, []);
  const addDemoMessage = useCallback(async (text: string) => {
    if (conversationDemoState.addMessage(activeId, text)) setRenderVersion((version) => version + 1);
  }, [activeId]);
  const acknowledgeDisplayed = useCallback(async (sequence: number) => {
    if (conversationDemoState.markDisplayed(activeId, sequence)) setRenderVersion((version) => version + 1);
  }, [activeId]);

  return (
    <div className="conversation-demo">
      <aside className="conversation-demo__warning" role="note">
        <strong>Development demo · synthetic data only</strong>
        <span>
          No account, API, or encryption service is connected. Messages you type are not encrypted,
          are not sent anywhere, and disappear when this page reloads. Unread badges update locally
          as messages are displayed and also reset on reload. Do not enter real messages.
        </span>
      </aside>
      {page === 'inbox' ? (
        <ConversationInbox
          conversations={conversationDemoState.getInboxItems()}
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
            last_read_sequence={conversationDemoState.getLastReadSequence(activeId)}
            presentationMode="local-demo"
            onRefresh={refresh}
            onSend={addDemoMessage}
            onRetry={async () => undefined}
            onAcknowledgeDisplayed={acknowledgeDisplayed}
          />
        </>
      )}
    </div>
  );
}
