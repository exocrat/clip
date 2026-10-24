import { lazy, Suspense, useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import type { ChallengeAccepted } from '../../../../../contracts/generated/types.gen';
import { Button } from '../../shared/ui';
import { identityApi, safeError } from './api';
import { useIdentity } from './session';
import './identity.css';

type Mode = 'login' | 'register' | 'verify';
const preview = import.meta.env.DEV && import.meta.env.MODE === 'identity-preview';
const PreviewMailbox = preview ? lazy(() => import('./PreviewMailbox')) : null;

/** Temporary credential/verification UI; secrets stay only in the current form.
 * Explicit user submission drives every write. A retry of an uncertain challenge
 * reuses its operation ID; deliberate resend uses a fresh ID after cooldown.
 */
export function SignIn() {
  const { status, user, accept } = useIdentity();
  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [challenge, setChallenge] = useState<ChallengeAccepted | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [seconds, setSeconds] = useState(0);
  const sending = useRef(false);
  const operation = useRef<{
    email: string;
    id: string;
    acknowledged: boolean;
  } | null>(null);
  useEffect(() => {
    if (seconds <= 0) return;
    const timer = setTimeout(() => setSeconds(seconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [seconds]);
  function change(next: Mode) {
    if (sending.current) return;
    setMode(next);
    setPassword('');
    setCode('');
    setError('');
    setNotice('');
    setChallenge(null);
    operation.current = null;
  }
  async function act(work: () => Promise<void>) {
    if (sending.current) return;
    sending.current = true;
    setBusy(true);
    setError('');
    try {
      await work();
    } catch (failure) {
      setError(safeError(failure));
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }
  async function issue(resend = false) {
    const target = email.trim();
    if (operation.current?.email !== target || (resend && operation.current.acknowledged))
      operation.current = {
        email: target,
        id: crypto.randomUUID(),
        acknowledged: false,
      };
    const result = await identityApi.register({
      email: target,
      operation_id: operation.current.id,
    });
    operation.current.acknowledged = true;
    setChallenge(result);
    setCode('');
    setMode('verify');
    setSeconds(60);
    setNotice(
      'If this address is eligible, a verification code will be sent. Check your inbox and spam folder.',
    );
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void act(async () => {
      if (mode === 'register') {
        await issue();
        return;
      }
      if (mode === 'verify') {
        if (!challenge || Date.parse(challenge.expires_at) <= Date.now()) {
          setError('This code has expired. Request a new code.');
          return;
        }
        const result = await identityApi.activate({
          challenge_id: challenge.challenge_id,
          code,
          password,
        });
        setPassword('');
        setCode('');
        setEmail('');
        setChallenge(null);
        operation.current = null;
        setMode('login');
        setSeconds(0);
        setNotice('');
        accept(result);
      } else {
        const result = await identityApi.login({
          email: email.trim(),
          password,
        });
        setPassword('');
        setEmail('');
        accept(result);
      }
    });
  }
  if (status === 'ready' && user)
    return (
      <section className="identity-card" aria-label="Signed in">
        <p className="identity-eyebrow">Your account</p>
        <h2>You’re signed in</h2>
        <p>
          {user.account_class === 'temporary'
            ? 'Your temporary account is valid for 14 days from verification.'
            : 'You’re signed in with your IISc account.'}
        </p>
        <p>
          Access ends at the server’s account or session deadline. Signing in again does not renew a
          temporary account.
        </p>
        <Link to="/">Continue to discover</Link>
      </section>
    );
  return (
    <div className="identity-layout">
      <section className="identity-intro">
        <p className="identity-eyebrow">Campus Marketplace</p>
        <h2>A place for the campus to exchange.</h2>
        <p>Sign in to save finds, post wanted requests, and talk privately with other members.</p>
        <p>
          Temporary accounts can browse, save, and contact sellers for 14 days. Publishing sale
          listings requires an eligible IISc account.
        </p>
      </section>
      <section className="identity-card" aria-label="Sign-in options">
        {preview && (
          <p className="identity-preview" role="note">
            Local test preview · synthetic accounts only · no email is sent. Microsoft sign-in is
            unavailable in this preview.
          </p>
        )}
        <h2>
          {mode === 'login'
            ? 'Welcome back'
            : mode === 'register'
              ? 'Create a temporary account'
              : 'Verify your email'}
        </h2>
        <p className="identity-muted">
          {mode === 'login'
            ? 'Use your verified temporary account.'
            : mode === 'register'
              ? 'We’ll send a code to verify your personal email.'
              : 'Enter the six-digit code and choose your password.'}
        </p>
        {status === 'loading' && <p role="status">Checking your session…</p>}
        {status === 'unavailable' && (
          <p role="status">Session status is unavailable. You can try signing in.</p>
        )}
        {notice && (
          <p role="status" className="identity-notice">
            {notice}
          </p>
        )}
        {error && (
          <p role="alert" className="identity-error">
            {error}
          </p>
        )}
        <form
          onSubmit={submit}
          aria-label={mode === 'verify' ? 'Verify temporary account' : 'Temporary account'}
        >
          {mode !== 'verify' && (
            <label>
              Email address
              <input
                name="email"
                type="email"
                autoComplete="email"
                required
                maxLength={254}
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  operation.current = null;
                }}
                disabled={busy}
              />
            </label>
          )}
          {mode === 'verify' && (
            <>
              <p>
                Code requested for <strong className="identity-wrap">{email}</strong>.
              </p>
              <label>
                Verification code
                <input
                  name="code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]{6}"
                  minLength={6}
                  maxLength={6}
                  required
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                  disabled={busy}
                />
              </label>
            </>
          )}
          {mode !== 'register' && (
            <>
              <label>
                Password
                <input
                  name="password"
                  type="password"
                  autoComplete={mode === 'verify' ? 'new-password' : 'current-password'}
                  required
                  minLength={mode === 'verify' ? 8 : undefined}
                  maxLength={128}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  disabled={busy}
                  aria-describedby={mode === 'verify' ? 'password-help' : undefined}
                />
              </label>
              {mode === 'verify' && (
                <p id="password-help" className="identity-muted">
                  Use 8–128 characters. Spaces are allowed.
                </p>
              )}
            </>
          )}
          <Button type="submit" disabled={busy || status === 'loading'}>
            {busy
              ? 'Please wait…'
              : mode === 'login'
                ? 'Sign in'
                : mode === 'register'
                  ? 'Send verification code'
                  : 'Verify and create account'}
          </Button>
        </form>
        {PreviewMailbox && (
          <Suspense fallback={<p>Loading test inbox…</p>}>
            <PreviewMailbox />
          </Suspense>
        )}
        <div className="identity-actions">
          {mode === 'login' ? (
            <Button variant="secondary" disabled={busy} onClick={() => change('register')}>
              Create temporary account
            </Button>
          ) : (
            <Button variant="secondary" disabled={busy} onClick={() => change('login')}>
              Back to sign in
            </Button>
          )}
          {mode === 'verify' && (
            <>
              <Button
                variant="secondary"
                disabled={busy || seconds > 0}
                onClick={() => {
                  void act(() => issue(true));
                }}
              >
                {seconds > 0 ? `Resend in ${seconds}s` : 'Send a new code'}
              </Button>
              <Button variant="secondary" disabled={busy} onClick={() => change('register')}>
                Use another email
              </Button>
            </>
          )}
        </div>
      </section>
    </div>
  );
}

/** Shell connection exposes session status without source contacts or credentials. */
export function IdentitySessionControl() {
  const { status, user, clear, refresh } = useIdentity();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function logout() {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      await identityApi.logout();
      clear();
    } catch (failure) {
      setError(safeError(failure));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="identity-session">
      {status === 'ready' && user ? (
        <>
          <span>
            {user.display_name ||
              (user.account_class === 'regular' ? 'IISc account' : 'Temporary account')}
          </span>
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => {
              void logout();
            }}
          >
            {busy ? 'Signing out…' : 'Sign out'}
          </Button>
        </>
      ) : status === 'loading' ? (
        <span role="status">Checking session…</span>
      ) : status === 'unavailable' ? (
        <Button
          variant="secondary"
          onClick={() => {
            void refresh();
          }}
        >
          Retry session check
        </Button>
      ) : (
        <Link to="/sign-in">Sign in</Link>
      )}
      {error && <span role="alert">{error}</span>}
    </div>
  );
}
