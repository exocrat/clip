import { IdentityProvider } from './features/identity';
import { AppRouter } from './app/router';

/** Provides Identity session state around the approved route tree. */
export function App() {
  return (
    <IdentityProvider>
      <AppRouter />
    </IdentityProvider>
  );
}
