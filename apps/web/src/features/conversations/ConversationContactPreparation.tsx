import { useEffect, useRef, useState } from 'react';
import type { ContactOptionsView, SelectedOwnContacts } from '../../../../../contracts/generated/types.gen';
import { Button } from '../../shared/ui';
import type { ContactField, ConversationApi } from './api';

const choices = [
  { field: 'email', flag: 'email_available', label: 'Email' },
  { field: 'phone', flag: 'phone_available', label: 'Phone' },
  { field: 'upi_id', flag: 'upi_available', label: 'UPI ID' },
] as const;

/** Explicit selection/confirmation only. Encrypted publication belongs to Step8.
 * Returned values are deliberately never placed in UI, storage, or diagnostics.
 */
export function ConversationContactPreparation({ conversationId, api, canShare, onShare, onRetry }: {
  conversationId: string;
  api: Pick<ConversationApi, 'readContactOptions' | 'prepareOwnContacts'>;
  canShare: boolean;
  onShare: (contacts: SelectedOwnContacts, operationId: string) => Promise<void>;
  onRetry: (operationId: string) => Promise<void>;
}) {
  const [options, setOptions] = useState<ContactOptionsView | null>(null);
  const [fields, setFields] = useState<ContactField[]>([]);
  const [review, setReview] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [retryOperationId, setRetryOperationId] = useState<string | null>(null);
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);

  function cancel() {
    active.current?.abort();
    setOptions(null);
    setFields([]);
    setReview(false);
    setBusy(false);
    setMessage('');
    setRetryOperationId(null);
  }
  async function load() {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    setMessage('');
    setOptions(null);
    setFields([]);
    setReview(false);
    try {
      const value = await api.readContactOptions(conversationId, controller.signal);
      if (!controller.signal.aborted) setOptions(value);
    } catch {
      if (!controller.signal.aborted) setMessage('Couldn’t load your contact options. Try again.');
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  async function confirm() {
    if (!review || !fields.length || busy) return;
    const controller = new AbortController();
    const operationId = crypto.randomUUID();
    active.current = controller;
    setBusy(true);
    setMessage('');
    let prepared = false;
    try {
      const contacts = await api.prepareOwnContacts(conversationId, fields, controller.signal);
      prepared = true;
      await onShare(contacts, operationId);
      if (!controller.signal.aborted) {
        setOptions(null);
        setFields([]);
        setReview(false);
        setRetryOperationId(null);
        setMessage('Encrypted contact details sent.');
      }
    } catch {
      if (!controller.signal.aborted) {
        if (prepared) {
          setRetryOperationId(operationId);
          setMessage('Couldn’t confirm whether the share was sent. Check the conversation before trying again.');
        } else {
          setMessage('Couldn’t prepare your selected details. Nothing was sent. Reload your contact options and try again.');
        }
      }
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  async function retryShare() {
    if (!retryOperationId || busy) return;
    setBusy(true);
    setMessage('');
    try {
      await onRetry(retryOperationId);
      setRetryOperationId(null);
      setMessage('Encrypted contact details sent.');
    } catch {
      setMessage('The share is still unconfirmed. Retry this same share or refresh the conversation.');
    } finally { setBusy(false); }
  }
  return <section aria-label="Prepare own contact details">
    <h3>Contact details</h3>
    <p>Choose your own details and confirm before they are encrypted and shared with the other participant.</p>
    {!canShare ? <p role="status">Set up encryption in this conversation before sharing contact details.</p> : null}
    {retryOperationId ? <Button disabled={busy || !canShare} onClick={() => void retryShare()} variant="secondary">Retry this contact share</Button> : null}
    {!options ? <Button disabled={busy} onClick={() => void load()}>Choose contact details</Button> : review ? <>
      <p>Confirm for this conversation: {choices.filter((choice) => fields.includes(choice.field)).map((choice) => choice.label).join(', ')}.</p>
      <Button disabled={busy || !canShare} onClick={() => void confirm()}>Confirm and send encrypted details</Button>
      <Button disabled={busy} onClick={() => setReview(false)} variant="secondary">Back</Button>
    </> : <>
      <fieldset disabled={busy}>
        <legend>Your available contact types</legend>
        {choices.map(({ field, flag, label }) => <label key={field}>
          <input type="checkbox" disabled={!options[flag]} checked={fields.includes(field)}
            onChange={(event) => setFields(event.target.checked ? [...fields, field] : fields.filter((value) => value !== field))} />
          {label}{options[flag] ? '' : ' (not set)'}
        </label>)}
      </fieldset>
      {!choices.some(({ flag }) => options[flag]) ? <p>Add contact details in Contact settings first.</p> : null}
      <Button disabled={!fields.length || busy} onClick={() => setReview(true)}>Review selected details</Button>
      <Button disabled={busy} onClick={() => void load()} variant="secondary">Reload contact options</Button>
    </>}
    {options ? <Button disabled={busy} onClick={cancel} variant="secondary">Cancel</Button> : null}
    {busy ? <p role="status">Checking your contact details…</p> : null}
    {message ? <p role="status">{message}</p> : null}
  </section>;
}
