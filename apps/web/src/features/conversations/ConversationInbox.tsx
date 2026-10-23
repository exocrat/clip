import { Button } from '../../shared/ui';
import './ConversationInbox.css';

export type ConversationInboxItem = {
  conversation_id: string;
  label: string;
  role: 'buyer' | 'seller' | 'request responder' | 'request author';
  last_activity_at: string;
  unread_count: number;
};

export type ConversationInboxProps = {
  conversations: ConversationInboxItem[];
  loading?: boolean;
  loadError?: boolean;
  onRefresh: () => Promise<void>;
  onOpen: (conversationId: string) => void;
};

/** Participant-scoped inbox presentation; data and authorization stay with its caller. */
export function ConversationInbox({
  conversations,
  loading = false,
  loadError = false,
  onRefresh,
  onOpen,
}: ConversationInboxProps) {
  return (
    <section aria-labelledby="conversation-inbox-title" className="conversation-inbox">
      <header className="conversation-inbox__header">
        <div>
          <h2 id="conversation-inbox-title">Your conversations</h2>
          <p>Private messages are encrypted on your device.</p>
        </div>
        <Button
          disabled={loading}
          onClick={() => void onRefresh().catch(() => undefined)}
          variant="secondary"
        >
          {loading ? 'Refreshing…' : 'Refresh'}
        </Button>
      </header>
      {loadError ? (
        <p className="conversation-inbox__notice" role="status">
          Couldn’t load conversations. Try refreshing.
        </p>
      ) : null}
      {loading && conversations.length === 0 ? (
        <p role="status">Loading conversations…</p>
      ) : conversations.length === 0 ? (
        <p className="conversation-inbox__empty">No conversations yet.</p>
      ) : (
        <ul className="conversation-inbox__list">
          {conversations.map((conversation) => (
            <li key={conversation.conversation_id}>
              <Button
                aria-label={`Open ${conversation.label}`}
                className="conversation-inbox__item"
                onClick={() => onOpen(conversation.conversation_id)}
                variant="secondary"
              >
                <span className="conversation-inbox__item-copy">
                  <span className="conversation-inbox__label">{conversation.label}</span>
                  <span className="conversation-inbox__meta">
                    {conversation.role} · {formatActivityTime(conversation.last_activity_at)}
                  </span>
                </span>
                {conversation.unread_count > 0 ? (
                  <span className="conversation-inbox__unread">
                    <span aria-hidden="true">{conversation.unread_count}</span>
                    <span className="conversation-inbox__sr-only">
                      {conversation.unread_count} unread
                    </span>
                  </span>
                ) : null}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function formatActivityTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'recent activity' : date.toLocaleString();
}
