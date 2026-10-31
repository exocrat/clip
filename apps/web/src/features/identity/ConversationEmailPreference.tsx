import { useEffect, useState } from 'react';
import { Button } from '../../shared/ui';
import { IdentityError, request } from './api';

/** Own-account control; failures hide the value until the server is read again. */
export function ConversationEmailPreference({ onUnauthorized }: { onUnauthorized: () => void }) {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setEnabled(null);
    setError('');
    void request('/me/conversation-email-preference', 'GET', undefined, false, controller.signal).then((value) => {
      if (!value || typeof value !== 'object' || !('enabled' in value) || typeof value.enabled !== 'boolean') throw new Error();
      if (!controller.signal.aborted) setEnabled(value.enabled);
    }).catch((failure: unknown) => {
      if (controller.signal.aborted) return;
      if (failure instanceof IdentityError && failure.status === 401) onUnauthorized();
      else setError('Could not load email preferences. Try again.');
    });
    return () => controller.abort();
  }, [onUnauthorized, reload]);

  async function change(value: boolean) {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const result = await request('/me/conversation-email-preference', 'PUT', { enabled: value }, true);
      if (!result || typeof result !== 'object' || !('enabled' in result) || result.enabled !== value) throw new Error();
      setEnabled(value);
    } catch (failure) {
      setEnabled(null);
      if (failure instanceof IdentityError && failure.status === 401) onUnauthorized();
      else setError('Could not confirm the change. Reload your email preference.');
    } finally { setBusy(false); }
  }

  return <section className="identity-card" aria-labelledby="conversation-email-title">
    <h2 id="conversation-email-title">Conversation emails</h2>
    <p>Receive emails about new conversations and unread messages. Verification and password-reset emails are unaffected.</p>
    {enabled === null ? <p role="status">{error || 'Loading email preference…'}</p> :
      <label><input type="checkbox" checked={enabled} disabled={busy} onChange={(event) => void change(event.target.checked)} /> Email me about conversations</label>}
    {error && <Button variant="secondary" onClick={() => setReload((value) => value + 1)}>Reload email preference</Button>}
  </section>;
}
