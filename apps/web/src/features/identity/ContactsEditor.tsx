import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import type { OwnContacts } from '../../../../../contracts/generated/types.gen';
import { Button } from '../../shared/ui';
import { identityApi, IdentityError, safeError, type ContactKind } from './api';
import { useIdentity } from './session';
import './identity.css';

const fields = [
  {
    kind: 'email',
    label: 'Contact email',
    name: 'Email',
    hint: 'An email address you choose to share.',
    type: 'text',
    inputMode: 'email',
    maxLength: 508,
  },
  {
    kind: 'phone',
    label: 'Phone number',
    name: 'Phone',
    hint: 'Use + followed by 8–15 digits, including the country code.',
    type: 'tel',
    inputMode: 'tel',
    maxLength: 16,
  },
  {
    kind: 'upi_id',
    label: 'UPI ID',
    name: 'UPI ID',
    hint: 'A UPI ID such as name@bank. Maximum 100 ASCII characters.',
    type: 'text',
    inputMode: 'text',
    maxLength: 100,
  },
] as const;
const empty = (): Record<ContactKind, string> => ({ email: '', phone: '', upi_id: '' });

/** Own-only page gate. Keying by the authenticated actor discards private drafts
 * and invalidates old reads/writes on logout or known account/class change.
 * No actor ID or return-navigation target is accepted from a browser parameter.
 */
export function ContactsEditor() {
  const identity = useIdentity();
  if (identity.status === 'loading') return <p role="status">Checking your session…</p>;
  if (identity.status === 'anonymous' || (!identity.user && identity.status !== 'unavailable')) {
    return (
      <section className="identity-card">
        <h2>Sign in to open Account</h2>
        <Link to="/sign-in">Go to sign in</Link>
      </section>
    );
  }
  if (identity.status === 'unavailable' || !identity.user)
    return (
      <section className="identity-card">
        <p role="alert">Session status is unavailable. Contact details are hidden.</p>
        <Button
          onClick={() => {
            void identity.refresh();
          }}
        >
          Retry session check
        </Button>
      </section>
    );
  return (
    <OwnedContactsEditor
      key={`${identity.user.user_id}:${identity.user.account_class}`}
      onUnauthorized={identity.clear}
    />
  );
}

/** In-memory drafts only; reads use a generation fence and writes never auto-retry.
 * A successful mutation is refetched before rendering saved values. Unknown
 * outcomes/read failures hide source values until an explicit safe read succeeds.
 */
function OwnedContactsEditor({ onUnauthorized }: { onUnauthorized: () => void }) {
  const [contacts, setContacts] = useState<OwnContacts | null>(null);
  const [drafts, setDrafts] = useState(empty);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<ContactKind | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const alive = useRef(false);
  const generation = useRef(0);
  const writing = useRef(false);

  const hide = useCallback(() => {
    setContacts(null);
    setDrafts(empty());
  }, []);
  const reload = useCallback(
    async (preserve: Partial<Record<ContactKind, string>> = {}) => {
      const current = ++generation.current;
      hide();
      setLoading(true);
      setError('');
      try {
        const result = await identityApi.contacts();
        if (!alive.current || current !== generation.current) return;
        setContacts(result);
        setDrafts({
          email: result.email ?? '',
          phone: result.phone ?? '',
          upi_id: result.upi_id ?? '',
          ...preserve,
        });
      } catch (failure) {
        if (!alive.current || current !== generation.current) return;
        if (failure instanceof IdentityError && failure.status === 401) onUnauthorized();
        else setError(safeError(failure));
      } finally {
        if (alive.current && current === generation.current) setLoading(false);
      }
    },
    [hide, onUnauthorized],
  );

  useEffect(() => {
    alive.current = true;
    void reload();
    // The session provider revalidates on focus. Keep unfinished own drafts
    // during ordinary focus changes; known actor changes unmount this editor.
    return () => {
      alive.current = false;
      generation.current++;
    };
  }, [reload]);

  async function update(kind: ContactKind, remove = false) {
    if (writing.current || loading || !contacts) return;
    const value = drafts[kind].trim();
    if (!remove && (!value || Array.from(value).length > 254)) {
      setError('Check the contact format and try again.');
      return;
    }
    writing.current = true;
    const current = ++generation.current;
    setBusy(kind);
    setError('');
    setNotice('');
    try {
      if (remove) await identityApi.deleteContact(kind);
      else await identityApi.setContact(kind, { value });
      if (!alive.current || current !== generation.current) return;
      hide();
      const label = fields.find((field) => field.kind === kind)?.name ?? 'Contact';
      setNotice(`${label} ${remove ? 'deleted' : 'saved'}.`);
      const preserve: Partial<Record<ContactKind, string>> = {};
      for (const field of fields) {
        if (field.kind !== kind && drafts[field.kind] !== (contacts[field.kind] ?? '')) {
          preserve[field.kind] = drafts[field.kind];
        }
      }
      await reload(preserve);
    } catch (failure) {
      if (!alive.current || current !== generation.current) return;
      if (failure instanceof IdentityError && failure.status === 401) onUnauthorized();
      else if (failure instanceof IdentityError && failure.status === 422)
        setError('Check the contact format and try again.');
      else {
        hide();
        setError(
          failure instanceof IdentityError && failure.uncertain
            ? 'We could not confirm the change. Refresh your contacts before trying again.'
            : safeError(failure),
        );
      }
    } finally {
      writing.current = false;
      if (alive.current) setBusy(null);
    }
  }
  function submit(event: FormEvent<HTMLFormElement>, kind: ContactKind) {
    event.preventDefault();
    void update(kind);
  }

  return (
    <section aria-label="Own contact editor" className="identity-contacts">
      {import.meta.env.DEV && import.meta.env.MODE === 'identity-preview' && (
        <p role="note" className="identity-preview">
          Local test preview. Use synthetic contact details only.
        </p>
      )}
      <p>Keep the details you want to share. Saving them here does not share them with anyone.</p>
      <p className="identity-muted">
        Changing contact email does not change your sign-in email. Deleting a contact removes it
        from future sharing. Copies you have already shared may remain.
      </p>
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
      {loading && <p role="status">Loading your contact details…</p>}
      <div className="identity-actions">
        <Button
          variant="secondary"
          disabled={loading || busy !== null}
          onClick={() => {
            setNotice('');
            void reload();
          }}
        >
          Refresh contacts
        </Button>
        <Link to="/my/conversations">Go to conversations</Link>
      </div>
      {contacts && (
        <div className="identity-contact-grid">
          {fields.map((field) => (
            <section className="identity-card" key={field.kind}>
              <h2>{field.name}</h2>
              {contacts[field.kind] === null && (
                <p className="identity-muted">No saved {field.name.toLowerCase()}.</p>
              )}
              <form
                aria-label={`${field.name} contact`}
                onSubmit={(event) => submit(event, field.kind)}
                autoComplete="off"
              >
                <label htmlFor={`contact-${field.kind}`}>{field.label}</label>
                <input
                  id={`contact-${field.kind}`}
                  name={field.kind}
                  type={field.type}
                  inputMode={field.inputMode}
                  maxLength={field.maxLength}
                  required
                  value={drafts[field.kind]}
                  onChange={(event) =>
                    setDrafts((current) => ({ ...current, [field.kind]: event.target.value }))
                  }
                  disabled={busy !== null}
                  aria-describedby={`contact-help-${field.kind}`}
                />
                <p id={`contact-help-${field.kind}`} className="identity-muted">
                  {field.hint}
                </p>
                <Button
                  type="submit"
                  disabled={
                    busy !== null ||
                    !drafts[field.kind].trim() ||
                    drafts[field.kind].trim() === contacts[field.kind]
                  }
                >
                  {busy === field.kind ? 'Please wait…' : `Save ${field.name.toLowerCase()}`}
                </Button>
                <Button
                  variant="secondary"
                  disabled={busy !== null || contacts[field.kind] === null}
                  onClick={() => {
                    void update(field.kind, true);
                  }}
                >
                  Delete {field.name.toLowerCase()}
                </Button>
              </form>
            </section>
          ))}
        </div>
      )}
    </section>
  );
}
