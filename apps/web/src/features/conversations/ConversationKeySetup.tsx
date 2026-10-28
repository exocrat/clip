import { useEffect, useRef, useState, type PropsWithChildren } from 'react';
import { Link, useLocation } from 'react-router';
import { Button } from '../../shared/ui';
import { sessionFetch } from '../../shared/http/sessionFetch';
import { ConversationApi } from './api';
import { openIndexedDbConversationSession } from './relay';
import { ConversationKeyStateLostError, KEY_REGISTRATION_WARNING, KeyRegistrationAcknowledgementRequiredError } from './crypto';

/** First-device setup publishes real SDK keys before normal marketplace use.
 * Returning logins quietly resume existing keys. Lost keys are never replaced;
 * contact editing remains reachable while setup is pending. The shell supplies
 * logout, so an outage never traps an account in a private feature.
 */
export function ConversationKeySetup({ userId, children }: PropsWithChildren<{ userId: string | null }>) {
  return userId ? <AccountKeySetup key={userId} userId={userId}>{children}</AccountKeySetup> : children;
}
function AccountKeySetup({ userId, children }: PropsWithChildren<{ userId: string }>) {
  const [state, setState] = useState<'checking' | 'consent' | 'ready' | 'lost' | 'error'>('checking');
  const [consent, setConsent] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const approved = useRef(false);
  const location = useLocation();
  useEffect(() => {
    let active = true;
    setState('checking');
    void openIndexedDbConversationSession(userId, null, new ConversationApi(sessionFetch),
      approved.current ? { acknowledgeUnrecoverableHistoryRisk: true } : {}).then(async (session) => {
        await session.stop();
        if (active) setState('ready');
      }).catch((error: unknown) => {
        if (active) setState(error instanceof KeyRegistrationAcknowledgementRequiredError ? 'consent' :
          error instanceof ConversationKeyStateLostError ? 'lost' : 'error');
      });
    return () => { active = false; };
  }, [userId, attempt]);
  if (state === 'ready') return children;
  return <>
    <section className="route-page" aria-label="Account encryption setup">
      <h2>Set up private messaging</h2>
      {state === 'checking' ? <p role="status">Checking this browser’s encryption setup…</p> : state === 'lost' ? <p role="alert">This browser is missing your account’s encryption keys. Use the browser where you set up messaging. CLIP cannot restore lost keys; they have not been replaced.</p> : state === 'error' ? <p role="alert">Couldn’t complete encryption setup. Your existing keys have been preserved. Try again in this browser.</p> : <>
        <p>{KEY_REGISTRATION_WARNING}</p>
        <label><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /> I understand that lost browser key data cannot be restored.</label>
        <Button disabled={!consent} onClick={() => { approved.current = true; setAttempt((value) => value + 1); }}>Create encryption key</Button>
      </>}
      {state === 'error' ? <Button onClick={() => setAttempt((value) => value + 1)}>Retry encryption setup</Button> : null}
      <p>You only set this up once in this browser. It lets people message you without waiting for you to open a conversation.</p>
      <Link className="ui-button ui-button--secondary" to="/account/contacts">Set up contact details (optional)</Link>
    </section>
    {location.pathname === '/account/contacts' ? children : null}
  </>;
}
