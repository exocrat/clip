import { useEffect, useRef, useState, type PropsWithChildren } from 'react';
import { Button } from '../../shared/ui';
import { sessionFetch } from '../../shared/http/sessionFetch';
import { ConversationApi } from './api';
import { openIndexedDbConversationSession } from './relay';
import { ConversationKeyStateLostError, KEY_REGISTRATION_WARNING, KeyRegistrationAcknowledgementRequiredError } from './crypto';
import './ConversationKeySetup.css';

/** Key readiness gates marketplace use after sign-in on this browser.
 * Existing local keys resume quietly. If this browser has lost them, a new key
 * can be published only after an explicit history-loss acknowledgement.
 */
export function ConversationKeySetup({ userId, children }: PropsWithChildren<{ userId: string | null }>) {
  return userId ? <AccountKeySetup key={userId} userId={userId}>{children}</AccountKeySetup> : children;
}
function AccountKeySetup({ userId, children }: PropsWithChildren<{ userId: string }>) {
  const [state, setState] = useState<'checking' | 'consent' | 'ready' | 'lost' | 'error'>('checking');
  const [consent, setConsent] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const approved = useRef(false);
  const replaceMissingIdentity = useRef(false);
  useEffect(() => {
    let active = true;
    setState('checking');
    void openIndexedDbConversationSession(userId, null, new ConversationApi(sessionFetch),
      approved.current ? {
        acknowledgeUnrecoverableHistoryRisk: true,
        ...(replaceMissingIdentity.current ? { allowUnrecoverableKeyReplacement: true } : {}),
      } : {}).then(async (session) => {
        await session.stop();
        if (active) {
          approved.current = false;
          replaceMissingIdentity.current = false;
          setConsent(false);
          setState('ready');
        }
      }).catch((error: unknown) => {
        if (active) setState(error instanceof KeyRegistrationAcknowledgementRequiredError ? 'consent' :
          error instanceof ConversationKeyStateLostError ? 'lost' : 'error');
      });
    return () => { active = false; };
  }, [userId, attempt]);
  if (state === 'ready') return children;
  const lost = state === 'lost';
  const createKey = () => {
    approved.current = true;
    replaceMissingIdentity.current = lost;
    setAttempt((value) => value + 1);
  };
  return <section className="conversation-key-setup" aria-label="Account encryption setup">
      <h2>{lost ? 'Create a new encryption key' : 'Set up private messaging'}</h2>
      {state === 'checking' ? <p role="status">Checking this browser’s encryption setup…</p> : lost ? <p role="alert">This browser does not have your current encryption key. CLIP cannot restore it. Replacing the account key lets you use this browser again, but encrypted conversations and contact shares may become inaccessible on other devices. Other members may need to accept your replacement key.</p> : state === 'error' ? <p role="alert">Couldn’t complete encryption setup. Your existing keys have been preserved. Try again in this browser.</p> : <p>{KEY_REGISTRATION_WARNING}</p>}
      {(state === 'consent' || lost) && <>
        <label className="conversation-key-setup__consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /> <span>I understand that lost browser key data cannot be restored.</span></label>
        <Button className="conversation-key-setup__create" disabled={!consent} onClick={createKey}>{lost ? 'Replace account encryption key' : 'Create encryption key'}</Button>
      </>}
      {state === 'error' ? <Button onClick={() => setAttempt((value) => value + 1)}>Retry encryption setup</Button> : null}
      {state !== 'checking' && state !== 'error' && <p>Private messaging must be ready before you use the marketplace on this browser. Encryption keys stay on this device; CLIP cannot restore lost keys.</p>}
    </section>;
}
