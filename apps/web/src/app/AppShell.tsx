import { ConversationKeySetup } from '../features/conversations';
import { Link, NavLink, Outlet } from 'react-router';
import './AppShell.css';
import { IdentitySessionControl, useIdentity } from '../features/identity';

const previewRoutes = [
  { to: '/sign-in', label: 'Sign in' },
  { to: '/auth/callback', label: 'Auth callback' },
  { to: '/', label: 'Discover' },
  { to: '/listings/new', label: 'New listing', sellerOnly: true },
  { to: '/my/listings?view=wanted&create=wanted', label: 'New Wanted Request' },
  { to: '/listings/example', label: 'Listing detail' },
  { to: '/listings/example/edit', label: 'Edit listing', sellerOnly: true },
  { to: '/my/listings', label: 'My listings' },
  { to: '/saved', label: 'Saved' },
  { to: '/my/conversations', label: 'Conversations' },
  { to: '/my/conversations/example', label: 'Conversation' },
  { to: '/account/contacts', label: 'Contact settings' },
  { to: '/wanted/example', label: 'Wanted request' },
];

/** Supplies the shared scaffold navigation and renders the selected route. */
export function AppShell() {
  const { status, user } = useIdentity();
  const seller = status === 'ready' && user?.account_class === 'regular' && Date.parse(user.valid_until) > Date.now();
  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <Link className="app-shell__brand" to="/">Campus Marketplace</Link>
        <IdentitySessionControl />
        <nav aria-label="Scaffold route preview" className="app-shell__nav">
          {previewRoutes.filter((route) => !route.sellerOnly || seller).map(({ to, label }) => (
            <NavLink
              key={to}
              end={to === '/'}
              to={to}
              className={({ isActive }) =>
                isActive ? 'app-shell__link app-shell__link--active' : 'app-shell__link'
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <p className="app-shell__note">
          Marketplace links preview unfinished domain routes. Identity sign-in is being verified locally.
        </p>
      </header>
      <ConversationKeySetup userId={status === 'ready' ? user?.user_id ?? null : null}><Outlet /></ConversationKeySetup>
    </div>
  );
}
