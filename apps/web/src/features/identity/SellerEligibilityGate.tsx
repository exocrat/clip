import { Fragment, type PropsWithChildren } from 'react';
import { Link } from 'react-router';
import { useIdentity } from './session';

/** Mount seller UI only for a current regular session from the public /me result.
 * Server authorization remains authoritative on every mutation. Actor keys discard
 * unsaved form/image state on account switches; no feature-private import is used.
 */
export function SellerEligibilityGate({ children, action = 'create' }: PropsWithChildren<{ action?: 'create' | 'manage' }>) {
  const verb = action === 'create' ? 'create' : 'manage';
  const { status, user } = useIdentity();
  if (status === 'loading') return <p role="status">Checking seller eligibility…</p>;
  if (status === 'unavailable')
    return (
      <section>
        <p role="alert">Please sign in again to continue.</p>
        <Link to="/sign-in">Sign in</Link>
      </section>
    );
  if (status !== 'ready' || !user || Date.parse(user.valid_until) <= Date.now())
    return <p><Link to="/sign-in">Sign in with your IISc Microsoft account</Link> to {verb} sale listings.</p>;
  if (user.account_class !== 'regular')
    return (
      <section>
        <p>Temporary accounts cannot {verb} sale listings. Sign in with an eligible IISc Microsoft account to sell.</p>
        <Link to="/">Browse the marketplace</Link>
      </section>
    );
  return <Fragment key={user.user_id}>{children}</Fragment>;
}
