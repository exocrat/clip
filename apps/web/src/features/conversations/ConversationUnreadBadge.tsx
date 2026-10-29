import { useEffect, useState } from 'react';
import { sessionFetch } from '../../shared/http/sessionFetch';

/** Share one bounded aggregate poll across desktop navigation and the mobile Menu.
 * The actor fence hides old data immediately, before effect cleanup on logout.
 */
export function useConversationUnreadCount(userId: string | null) {
  const [state, setState] = useState<{ userId: string | null; count: number | null }>({ userId, count: null });
  useEffect(() => {
    if (!userId) return;
    const controller = new AbortController();
    let pending = false;
    const refresh = async () => {
      if (pending || document.visibilityState === 'hidden') return;
      pending = true;
      try {
        const response = await sessionFetch('/conversations/unread-count', { signal: controller.signal, cache: 'no-store' });
        if (!response.ok) throw new Error('Unavailable');
        const value: unknown = await response.json();
        if (!value || typeof value !== 'object' || !('unread_count' in value) || typeof value.unread_count !== 'number'
          || !Number.isSafeInteger(value.unread_count) || value.unread_count < 0) throw new Error('Invalid count');
        if (!controller.signal.aborted) setState({ userId, count: value.unread_count });
      } catch { if (!controller.signal.aborted) setState({ userId, count: null }); }
      finally { pending = false; }
    };
    void refresh();
    const timer = setInterval(() => void refresh(), 5000);
    document.addEventListener('visibilitychange', refresh);
    return () => { controller.abort(); clearInterval(timer); document.removeEventListener('visibilitychange', refresh); };
  }, [userId]);
  return state.userId === userId ? state.count : null;
}

export function ConversationUnreadBadge({ count }: { count: number | null }) {
  return count ? <span className="conversation-inbox__unread" role="status" aria-label={`${count} unread messages`}>{count}</span> : null;
}
