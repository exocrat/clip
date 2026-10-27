import { useMemo, type PropsWithChildren } from 'react';
import { useIdentity } from '../features/identity';
import { ConversationApi, ConversationPageRuntimeProvider } from '../features/conversations';
import { sessionFetch } from '../shared/http/sessionFetch';

/** Compose public session state with cookie/CSRF transport. Null unmounts private
 * chat controllers on logout/expiry; same-account session refresh preserves work.
 */
export function ConversationRuntime({ children }: PropsWithChildren) {
  const { status, user } = useIdentity();
  const userId = status === 'ready' && user ? user.user_id : null;
  const runtime = useMemo(() => userId
    ? { userId, api: new ConversationApi(sessionFetch) }
    : null, [userId]);
  return <ConversationPageRuntimeProvider runtime={runtime}>{children}</ConversationPageRuntimeProvider>;
}
