import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { Button } from '../../shared/ui';
import { completeMicrosoft, microsoftEnabled, MicrosoftSignInError } from './microsoft';
import { useIdentity } from './session';

/** Present the real provider action only when its explicit runtime gate permits it. */
export function MicrosoftSignInButton({
  disabled,
  onClick,
}: {
  disabled: boolean;
  onClick: () => void;
}) {
  const enabled = microsoftEnabled();
  return (
    <div className="identity-microsoft">
      <Button disabled={disabled || !enabled} onClick={onClick}>
        Continue with Microsoft
      </Button>
      <p className="identity-muted">
        {enabled
          ? 'Use your IISc Microsoft account. Eligibility is checked securely by CLIP.'
          : 'Microsoft sign-in is currently unavailable.'}
      </p>
    </div>
  );
}

/** Callback UI never renders provider URLs/claims; exchange deduplication is owned
 * by the controller, so React StrictMode cannot consume the server attempt twice.
 * A safe explicit GET may recover an already-established session after ambiguity.
 */
export function MicrosoftCallback() {
  const { accept, refresh } = useIdentity();
  const [phase, setPhase] = useState<'pending' | 'success' | 'recovered' | 'error'>('pending');
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(false);
  useEffect(() => {
    let active = true;
    void completeMicrosoft()
      .then((result) => {
        if (active) {
          accept(result);
          setPhase('success');
        }
      })
      .catch((failure) => {
        if (active) {
          setError(
            failure instanceof MicrosoftSignInError
              ? failure.message
              : 'We could not complete Microsoft sign-in.',
          );
          setPhase('error');
        }
      });
    return () => {
      active = false;
    };
  }, [accept]);
  async function checkSession() {
    if (checking) return;
    setChecking(true);
    try {
      const current = await refresh();
      if (current) setPhase('recovered');
      else setError('No current sign-in was confirmed. Return to sign in to start again.');
    } catch {
      setError('We could not check your current sign-in status.');
    } finally {
      setChecking(false);
    }
  }
  return (
    <section className="identity-card" aria-label="Microsoft sign-in result">
      {phase === 'pending' ? (
        <>
          <h2>Completing sign-in</h2>
          <p role="status">Checking your Microsoft sign-in…</p>
        </>
      ) : phase === 'success' || phase === 'recovered' ? (
        <>
          <h2>You’re signed in</h2>
          <p>
            {phase === 'success'
              ? 'Your IISc account is ready.'
              : 'Your current CLIP session is active.'}
          </p>
          <Link to="/">Continue to discover</Link>
        </>
      ) : (
        <>
          <h2>Sign-in could not be completed</h2>
          <p role="alert" className="identity-error">
            {error}
          </p>
          <div className="identity-actions">
            <Link to="/sign-in">Back to sign in</Link>
            <Button
              variant="secondary"
              disabled={checking}
              onClick={() => {
                void checkSession();
              }}
            >
              {checking ? 'Checking…' : 'Check sign-in status'}
            </Button>
          </div>
        </>
      )}
    </section>
  );
}
