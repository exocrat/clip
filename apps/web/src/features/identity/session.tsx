import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type PropsWithChildren,
} from 'react';
import type { SessionView } from '../../../../../contracts/generated/types.gen';
import { identityApi, IdentityError } from './api';

type SessionState = {
  status: 'loading' | 'anonymous' | 'ready' | 'unavailable';
  user: SessionView | null;
};
type SessionContext = SessionState & {
  refresh: () => Promise<SessionView | null>;
  accept: (user: SessionView) => void;
  clear: () => void;
};
const Context = createContext<SessionContext | null>(null);

/** In-memory session summary only. Server cookies remain HttpOnly and authoritative.
 * A generation fences stale reads after login/logout. Visibility rechecks and the
 * server deadline clear stale UI; every protected API still authorizes itself.
 */
export function IdentityProvider({ children }: PropsWithChildren) {
  const [state, setState] = useState<SessionState>({
    status: 'loading',
    user: null,
  });
  const generation = useRef(0);
  const clear = useCallback(() => {
    generation.current++;
    setState({ status: 'anonymous', user: null });
  }, []);
  const accept = useCallback((user: SessionView) => {
    generation.current++;
    if (Date.parse(user.valid_until) <= Date.now()) {
      setState({ status: 'anonymous', user: null });
      return;
    }
    setState({ status: 'ready', user });
  }, []);
  const refresh = useCallback(async () => {
    const current = ++generation.current;
    try {
      const user = await identityApi.me();
      if (current === generation.current) {
        accept(user);
        return user;
      }
    } catch (error) {
      if (current === generation.current)
        setState({
          status:
            error instanceof IdentityError && error.status === 401 ? 'anonymous' : 'unavailable',
          user: null,
        });
    }
    return null;
  }, [accept]);
  useEffect(() => {
    void refresh();
    const visible = () => {
      if (document.visibilityState === 'visible') void refresh();
    };
    window.addEventListener('focus', visible);
    document.addEventListener('visibilitychange', visible);
    return () => {
      generation.current++;
      window.removeEventListener('focus', visible);
      document.removeEventListener('visibilitychange', visible);
    };
  }, [refresh]);
  useEffect(() => {
    if (!state.user) return;
    const deadline = Date.parse(state.user.valid_until) - Date.now();
    const timer = setTimeout(clear, Math.min(Math.max(0, deadline), 2_147_483_647));
    return () => clearTimeout(timer);
  }, [state.user, clear]);
  return (
    <Context.Provider value={{ ...state, refresh, accept, clear }}>{children}</Context.Provider>
  );
}

/** Public feature hook: summary/capabilities aid presentation, never authorization. */
export function useIdentity() {
  const context = useContext(Context);
  if (!context) throw new Error('IdentityProvider is required');
  return context;
}
