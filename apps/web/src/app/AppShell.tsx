import { useState } from 'react';
import { useConversationUnreadCount, ConversationUnreadBadge, ConversationKeySetup } from '../features/conversations';
import { Link, NavLink, Outlet, useLocation } from 'react-router';
import './AppShell.css';
import { HandleSetup, IdentitySessionControl, useIdentity } from '../features/identity';

const productRoutes = [
  { to: '/', label: 'Discover' },
  { to: '/listings/new', label: 'New Listing', sellerOnly: true },
  { to: '/my/listings?view=wanted&create=wanted', label: 'New Wanted Request' },
  { to: '/my/listings', label: 'My Listings' },
  { to: '/saved', label: 'Saved' },
  { to: '/my/conversations', label: 'Conversations' },
  { to: '/account/contacts', label: 'Account' },
];

/** Supplies the shared scaffold navigation and renders the selected route. */
export function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const { status, user } = useIdentity();
  const unreadCount = useConversationUnreadCount(status === "ready" ? user?.user_id ?? null : null);
  const seller = status === 'ready' && user?.account_class === 'regular' && Date.parse(user.valid_until) > Date.now();
  const routes = status === 'anonymous' ? [{ to: '/sign-in', label: 'Sign in' }, ...productRoutes] : productRoutes;
  // Keep the one-time OAuth callback mounted until it completes and the user
  // navigates away; marketplace setup gates then run on the destination route.
  if (location.pathname === '/auth/callback') return <Outlet />;
  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <div className="app-shell__top">
          <Link className="app-shell__brand" to="/">Campus Marketplace</Link>
          {status !== 'anonymous' ? <div className="app-shell__account"><IdentitySessionControl /></div> : null}
        </div>
      </header>
      <ConversationKeySetup userId={status === 'ready' ? user?.user_id ?? null : null}>
        <div className="app-shell__workspace">
          <div className="app-shell__navigation">
            <button className="app-shell__menu" aria-expanded={menuOpen} aria-controls="marketplace-navigation" onClick={() => setMenuOpen(!menuOpen)} type="button">Menu <ConversationUnreadBadge count={unreadCount} /></button>
            <nav id="marketplace-navigation" aria-label="Marketplace" className={`app-shell__nav${menuOpen ? " app-shell__nav--open" : ""}`}>
              {routes.filter((route) => !('sellerOnly' in route) || !route.sellerOnly || seller).map(({ to, label }) => (
                <NavLink
                  onClick={() => setMenuOpen(false)}
                  key={to}
                  end={to === '/'}
                  to={to}
                  className={({ isActive }) =>
                    isActive ? 'app-shell__link app-shell__link--active' : 'app-shell__link'
                  }
                >
                  {label}{to === "/my/conversations" && status === "ready" && user && <ConversationUnreadBadge count={unreadCount} />}
                </NavLink>
              ))}
            </nav>
          </div>
          <HandleSetup><Outlet /></HandleSetup>
        </div>
      </ConversationKeySetup>
    </div>
  );
}
