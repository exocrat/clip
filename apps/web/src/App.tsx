import { IdentityProvider } from './features/identity';
import { AppRouter } from './app/router';
import { ConversationRuntime } from './pages/ConversationRuntime';

/** Provides Identity session state around the approved route tree. */
export function App() {
  return (
    <IdentityProvider>
      <ConversationRuntime><AppRouter /></ConversationRuntime>
    </IdentityProvider>
  );
}
