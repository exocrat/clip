import { lazy, Suspense, useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import type { ChallengeAccepted, SessionView } from '../../../../../contracts/generated/types.gen';
import { Button } from '../../shared/ui';
import { identityApi, IdentityError, safeError } from './api';
import { useIdentity } from './session';
import './identity.css';
import { MicrosoftSignInButton } from './MicrosoftSignIn';
import { beginMicrosoft, MicrosoftSignInError } from './microsoft';

type Mode = 'login' | 'register' | 'verify' | 'forgot' | 'reset';
const headings: Record<Mode, string> = {
  login: 'Welcome back',
  register: 'Create a temporary account',
  verify: 'Verify your email',
  forgot: 'Forgot your password?',
  reset: 'Choose a new password',
};
const actions: Record<Mode, string> = {
  login: 'Sign in',
  register: 'Send verification code',
  verify: 'Verify and create account',
  forgot: 'Send reset code',
  reset: 'Reset password',
};
const preview = import.meta.env.DEV && import.meta.env.MODE === 'identity-preview';
const PreviewMailbox = preview ? lazy(() => import('./PreviewMailbox')) : null;

/** Temporary credential/verification UI; secrets stay only in the current form.
 * Explicit user submission drives every write. A retry of an uncertain challenge
 * reuses its operation ID; deliberate resend uses a fresh ID after cooldown.
 */
export function SignIn() {
  const { status, user, accept, clear } = useIdentity();
  const [mode, setMode] = useState<Mode>('login');
  const creatingPassword = mode === 'verify' || mode === 'reset';
  const enteringEmail = mode === 'login' || mode === 'register' || mode === 'forgot';
  const resetting = mode === 'forgot' || mode === 'reset';
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
      setError(
        failure instanceof MicrosoftSignInError
          ? failure.message
          : failure instanceof IdentityError && failure.uncertain && mode === 'reset'
            ? 'We could not confirm the reset. Try signing in with your new password before requesting another code.'
            : failure instanceof IdentityError && failure.uncertain && mode === 'verify'
              ? 'We could not confirm account creation. Try signing in with the password you chose.'
              : safeError(failure),
      );
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
    const result = await (resetting ? identityApi.resetChallenge : identityApi.register)({
      email: target,
      operation_id: operation.current.id,
    });
    operation.current.acknowledged = true;
    setChallenge(result);
    setCode('');
    setMode(resetting ? 'reset' : 'verify');
    setSeconds(60);
    setNotice(
      'If this address is eligible, a verification code will be sent. Check your inbox and spam folder.',
    );
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void act(async () => {
      if (mode === 'register' || mode === 'forgot') {
        await issue();
        return;
      }
      if (creatingPassword) {
        // Include Unicode whitespace and the legacy C0 separators recognized by
        // Python's server-side policy. Never trim or rewrite the chosen password.
        const hasWhitespace = Array.from(password).some((character) =>
          /\s/u.test(character) || [0x85, 0x1c, 0x1d, 0x1e, 0x1f].includes(character.codePointAt(0) ?? 0),
        );
        if (Array.from(password).length < 8 || Array.from(password).length > 128 || hasWhitespace) {
          setError('Use 8–128 characters with no spaces or other whitespace.');
          return;
        }
        if (!challenge || Date.parse(challenge.expires_at) <= Date.now()) {
          setError('This code has expired. Request a new code.');
          return;
        }
        let result: SessionView | undefined;
        if (mode === 'reset') {
          await identityApi.resetPassword({
            challenge_id: challenge.challenge_id,
            code,
            new_password: password,
          });
          clear(); // Server reset revokes every session and issues no replacement.
        } else {
          result = await identityApi.activate({
            challenge_id: challenge.challenge_id,
            code,
            password,
          });
        }
        setPassword('');
        setCode('');
        setEmail('');
        setChallenge(null);
        operation.current = null;
        setMode('login');
        setSeconds(0);
        setNotice(mode === 'reset' ? 'Password changed. Sign in with your new password.' : '');
        if (result) accept(result);
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
        <p className="identity-eyebrow">CLIP</p>
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
        <h2>{headings[mode]}</h2>
        <p className="identity-muted">
          {mode === 'login'
            ? 'Use an eligible IISc Microsoft account or your verified temporary account.'
            : mode === 'register'
              ? 'We’ll send a code to verify your personal email.'
              : mode === 'forgot'
                ? 'Enter the email you used for your temporary account.'
                : 'Enter the six-digit code and choose your password.'}
        </p>
        {mode === 'login' && (
          <MicrosoftSignInButton
            disabled={busy || status === 'loading'}
            onClick={() => {
              void act(beginMicrosoft);
            }}
          />
        )}
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
          aria-label={
            mode === 'reset'
              ? 'Reset temporary password'
              : mode === 'verify'
                ? 'Verify temporary account'
                : 'Temporary account'
          }
        >
          {enteringEmail && (
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
          {creatingPassword && (
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
          {(mode === 'login' || creatingPassword) && (
            <>
              <label>
                {mode === 'reset' ? 'New password' : 'Password'}
                <input
                  name="password"
                  type="password"
                  autoComplete={creatingPassword ? 'new-password' : 'current-password'}
                  required
                  minLength={creatingPassword ? 8 : undefined}
                  maxLength={256}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  disabled={busy}
                  aria-describedby={creatingPassword ? 'password-help' : undefined}
                />
              </label>
              {creatingPassword && (
                <p id="password-help" className="identity-muted">
                  Use 8–128 characters. Spaces and other whitespace are not allowed.
                </p>
              )}
            </>
          )}
          <Button type="submit" disabled={busy || status === 'loading'}>
            {busy ? 'Please wait…' : actions[mode]}
          </Button>
        </form>
        {PreviewMailbox && (
          <Suspense fallback={<p>Loading test inbox…</p>}>
            <PreviewMailbox />
          </Suspense>
        )}
        <div className="identity-actions">
          {mode === 'login' ? (
            <>
              <Button variant="secondary" disabled={busy} onClick={() => change('register')}>
                Create temporary account
              </Button>
              <Button variant="secondary" disabled={busy} onClick={() => change('forgot')}>
                Forgot password
              </Button>
            </>
          ) : (
            <Button variant="secondary" disabled={busy} onClick={() => change('login')}>
              Back to sign in
            </Button>
          )}
          {creatingPassword && (
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
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => change(resetting ? 'forgot' : 'register')}
              >
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
  const { status, user, clear } = useIdentity();
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
      ) : (
        <Link to="/sign-in">Sign in</Link>
      )}
      {error && <span role="alert">{error}</span>}
    </div>
  );
}
