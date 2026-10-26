import { Fragment, type PropsWithChildren } from 'react';
import { Link } from 'react-router';
import { Button } from '../../shared/ui';
import { useIdentity } from './session';

/** Mount seller UI only for a current regular session from the public /me result.
 * Server authorization remains authoritative on every mutation. Actor keys discard
 * unsaved form/image state on account switches; no feature-private import is used.
 */
export function SellerEligibilityGate({ children }: PropsWithChildren) {
  const { status, user, refresh } = useIdentity();
  if (status === 'loading') return <p role="status">Checking seller eligibility…</p>;
  if (status === 'unavailable')
    return (
      <section>
        <p role="alert">We could not check your account. Try again before creating a listing.</p>
        <Button onClick={() => { void refresh(); }}>Check account again</Button>
      </section>
    );
  if (status !== 'ready' || !user || Date.parse(user.valid_until) <= Date.now())
    return <p><Link to="/sign-in">Sign in with your IISc Microsoft account</Link> to create a sale listing.</p>;
  if (user.account_class !== 'regular')
    return (
      <section>
        <p>Temporary accounts cannot create sale listings. Sign in with an eligible IISc Microsoft account to sell.</p>
        <Link to="/">Browse the marketplace</Link>
      </section>
    );
  return <Fragment key={user.user_id}>{children}</Fragment>;
}
