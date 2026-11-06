import { useEffect, useRef, useState, type FormEvent, type PropsWithChildren } from 'react';
import { Button } from '../../shared/ui';
import { IdentityError, request } from './api';
import { useIdentity } from './session';
import './identity.css';

/** Reuses the profile field; session refresh confirms server ownership of the claim. */
export function HandleEditor() {
  const { user } = useIdentity();
  return user ? <HandleEditorForm key={user.user_id} /> : null;
}
function HandleEditorForm() {
  const { user, refresh } = useIdentity();
  const [value, setValue] = useState(user?.display_name ?? '');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  async function save(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    const handle = value.trim();
    if (!/^[A-Za-z0-9_]{3,30}$/.test(handle)) {
      setMessage('Use 3–30 letters, numbers or underscores.');
      return;
    }
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    setMessage('');
    try {
      await request('/me/profile', 'PATCH', { display_name: handle }, true, controller.signal);
      if (controller.signal.aborted) return;
      await refresh();
      setMessage('Handle saved.');
    } catch (error) {
      if (controller.signal.aborted) return;
      setMessage(error instanceof IdentityError && error.status === 409
        ? 'That Handle is taken. Choose another.' : 'Could not save your Handle. Try again.');
    } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <section className="identity-card"><h2>Your Handle</h2>
    <p>Choose a unique Handle so people can recognize you in conversations. You can change it here later.</p>
    <form className="identity-handle-form" onSubmit={save}><label htmlFor="account-handle">Handle</label>
      <input id="account-handle" autoComplete="username" value={value} maxLength={64}
        onChange={(event) => setValue(event.target.value)} required disabled={busy} />
      <p>3–30 letters, numbers or underscores. Uppercase and lowercase count as the same name.</p>
      <Button type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save Handle'}</Button>
      {message && <p role="status">{message}</p>}
    </form></section>;
}

/** Upgraded sessions explicitly report incomplete setup; older fixtures omit the flag. */
export function HandleSetup({ children }: PropsWithChildren) {
  const { user, status } = useIdentity();
  return status === 'ready' && user?.handle_ready === false
    ? <HandleEditor key={user.user_id} /> : children;
}
