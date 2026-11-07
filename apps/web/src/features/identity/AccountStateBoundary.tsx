import { Fragment, type PropsWithChildren } from 'react';
import { Link } from 'react-router';
import { useIdentity } from './session';

/** Isolate marketplace view state by the current server-authenticated actor.
 * Unknown/ended sessions unmount private content immediately. Actor/class changes
 * remount it, discarding drafts and running feature cleanup/abort handlers. Stable
 * same-actor refreshes preserve work. Auth entry/callback pages must stay outside
 * this boundary so accepting a login cannot rerun a consumed callback.
 */
export function AccountStateBoundary({ children }: PropsWithChildren) {
  const { status, user } = useIdentity();
  if (status === 'loading') return <p role="status">Checking sign-in…</p>;
  if (status === 'unavailable')
    return <section><p role="alert">Please sign in again to continue.</p><Link to="/sign-in">Sign in</Link></section>;
  if (status !== 'ready' || !user || Date.parse(user.valid_until) <= Date.now())
    return <p><Link to="/sign-in">Sign in</Link> to view the marketplace.</p>;
  return <Fragment key={`${user.user_id}:${user.account_class}`}>{children}</Fragment>;
}
