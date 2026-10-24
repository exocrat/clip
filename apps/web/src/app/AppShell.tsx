import { Link, NavLink, Outlet } from 'react-router';
import './AppShell.css';
import { IdentitySessionControl } from '../features/identity';

const previewRoutes = [
  { to: '/sign-in', label: 'Sign in' },
  { to: '/auth/callback', label: 'Auth callback' },
  { to: '/', label: 'Discover' },
  { to: '/listings/new', label: 'New listing' },
  { to: '/listings/example', label: 'Listing detail' },
  { to: '/listings/example/edit', label: 'Edit listing' },
  { to: '/my/listings', label: 'My listings' },
  { to: '/saved', label: 'Saved' },
  { to: '/my/conversations', label: 'Conversations' },
  { to: '/my/conversations/example', label: 'Conversation' },
  { to: '/account/contacts', label: 'Contact settings' },
  { to: '/wanted/example', label: 'Wanted request' },
];

/** Supplies the shared scaffold navigation and renders the selected route. */
export function AppShell() {
  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <Link className="app-shell__brand" to="/">Campus Marketplace</Link>
        <IdentitySessionControl />
        <nav aria-label="Scaffold route preview" className="app-shell__nav">
          {previewRoutes.map(({ to, label }) => (
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
      <Outlet />
    </div>
  );
}
