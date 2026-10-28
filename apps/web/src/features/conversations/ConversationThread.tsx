import { useEffect, useMemo, useRef, useState } from 'react';
import { Button } from '../../shared/ui';
import { createDisplayedReadAcknowledger } from './read-state';
import {
  KEY_REGISTRATION_WARNING,
  PEER_KEY_CHANGE_WARNING,
} from './crypto';
import './ConversationThread.css';

export type ConversationDisplayEntry = {
  entry_id: string;
  sequence: number;
  sender_user_id: string;
  created_at: string;
  text: string | null;
  contact_details?: Partial<Record<'email' | 'phone' | 'upi_id', string>>;
  content_deleted: boolean;
  /** A peer's authenticated SDK retry request says this original message could not be decrypted. */
  delivery_notice?: 'recipient_unable_to_decrypt';
};

export type ConversationKeyUiState =
  | { kind: 'ready' }
  | { kind: 'waiting_for_peer_key' }
  | { kind: 'registration_acknowledgement_required' }
  | { kind: 'key_change'; participant_label: string }
  | { kind: 'key_state_lost' }
  | { kind: 'error' };

export type ConversationThreadProps = {
  current_user_id: string;
  entries: ConversationDisplayEntry[];
  key_state: ConversationKeyUiState;
  last_read_sequence: number;
  /** Changes only the privacy/call-to-action copy for a loopback synthetic demo. */
  presentationMode?: 'live' | 'local-demo';
  loading?: boolean;
  recoveredPending?: { operationId: string; text: string } | null;
  onRefresh: () => Promise<void>;
  onSend: (text: string, operationId: string) => Promise<void>;
  /** Retry must reuse the same operation ID and the originally prepared ciphertext. */
  onRetry: (operationId: string) => Promise<void>;
  onAcknowledgeDisplayed: (lastDisplayedSequence: number) => Promise<void>;
  onAcknowledgeKeyRegistration?: () => Promise<void>;
  onAcceptChangedKey?: () => Promise<void>;
};

type PendingSend = {
  operationId: string;
  text: string;
  state: 'sending' | 'failed';
};

const POLL_INTERVAL_MS = 2_000;
const MAX_POLL_BACKOFF_MS = 30_000;

/** Private-thread UI; message plaintext is rendered only and never persisted or logged here. */
export function ConversationThread({
  current_user_id,
  entries,
  key_state,
  last_read_sequence,
  presentationMode = 'live',
  loading = false,
  recoveredPending = null,
  onRefresh,
  onSend,
  onRetry,
  onAcknowledgeDisplayed,
  onAcknowledgeKeyRegistration,
  onAcceptChangedKey,
}: ConversationThreadProps) {
  const [draft, setDraft] = useState('');
  const [pending, setPending] = useState<PendingSend | null>(null);
  const [sendError, setSendError] = useState(false);
  const [refreshError, setRefreshError] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [acknowledgedRegistration, setAcknowledgedRegistration] = useState(false);
  const messageListRef = useRef<HTMLOListElement>(null);
  const canSend = key_state.kind === 'ready' && !pending && !actionBusy;

  useEffect(() => {
    if (!pending && recoveredPending) setPending({ ...recoveredPending, state: 'failed' });
  }, [pending, recoveredPending]);

  useEffect(() => {
    if (typeof document === 'undefined') return;

    let delay = POLL_INTERVAL_MS;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let inFlight = false;
    let disposed = false;
    const visible = () => document.visibilityState === 'visible';
    const schedule = () => {
      if (disposed || !visible() || inFlight) return;
      timer = setTimeout(() => void refresh(), delay);
    };
    const refresh = async () => {
      if (disposed || !visible() || inFlight) return;
      if (timer) clearTimeout(timer);
      inFlight = true;
      try {
        await onRefresh();
        delay = POLL_INTERVAL_MS;
        setRefreshError(false);
      } catch {
        setRefreshError(true);
        delay = Math.min(delay * 2, MAX_POLL_BACKOFF_MS);
      } finally {
        inFlight = false;
        schedule();
      }
    };
    const onVisibilityChange = () => {
      if (visible()) void refresh();
      else if (timer) clearTimeout(timer);
    };
    const onFocus = () => void refresh();

    void refresh();
    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('focus', onFocus);
    return () => {
      disposed = true;
      if (timer) clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.removeEventListener('focus', onFocus);
    };
  }, [onRefresh]);

  const acknowledgeDisplayed = useMemo(
    () => createDisplayedReadAcknowledger(onAcknowledgeDisplayed, last_read_sequence),
    [last_read_sequence, onAcknowledgeDisplayed],
  );
  useEffect(() => {
    const list = messageListRef.current;
    if (key_state.kind !== 'ready' || !list || typeof IntersectionObserver === 'undefined') return;
    const observer = new IntersectionObserver(
      (observed) => {
        // Intersection geometry alone does not mean the user can see a hidden tab.
        if (document.visibilityState !== 'visible') return;
        const visibleSequences = observed
          .filter((item) => item.isIntersecting && item.intersectionRatio >= 0.25)
          .map((item) => Number((item.target as HTMLElement).dataset.sequence))
          .filter((sequence) => Number.isSafeInteger(sequence) && sequence > last_read_sequence);
        const greatestDisplayed = Math.max(0, ...visibleSequences);
        if (greatestDisplayed > 0) void acknowledgeDisplayed(greatestDisplayed).catch(() => undefined);
      },
      { root: list, threshold: 0.25 },
    );
    list.querySelectorAll<HTMLElement>('[data-sequence]').forEach((item) => {
      observer.observe(item);
    });
    return () => observer.disconnect();
  }, [acknowledgeDisplayed, entries, key_state.kind, last_read_sequence]);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSend || !draft.trim()) return;
    const operationId = globalThis.crypto.randomUUID();
    const text = draft;
    setDraft('');
    setPending({ operationId, text, state: 'sending' });
    setSendError(false);
    try {
      await onSend(text, operationId);
      setPending(null);
    } catch {
      setPending({ operationId, text, state: 'failed' });
      setSendError(true);
    }
  };

  const retry = async () => {
    if (pending?.state !== 'failed' || actionBusy) return;
    setActionBusy(true);
    try {
      await onRetry(pending.operationId);
      setPending(null);
      setSendError(false);
    } catch {
      setSendError(true);
    } finally {
      setActionBusy(false);
    }
  };

  const acknowledgeAndRegister = async () => {
    if (!acknowledgedRegistration || !onAcknowledgeKeyRegistration) return;
    await runKeyAction(onAcknowledgeKeyRegistration);
  };

  const acceptChangedKey = async () => {
    if (!onAcceptChangedKey) return;
    await runKeyAction(onAcceptChangedKey);
  };

  const runKeyAction = async (action: () => Promise<void>) => {
    setActionBusy(true);
    try {
      await action();
    } catch {
      setSendError(true);
    } finally {
      setActionBusy(false);
    }
  };

  return (
    <section aria-label="Private conversation" className="conversation-thread">
      <div className="conversation-thread__privacy" role="note">
        {presentationMode === 'local-demo'
          ? 'Local demo only: messages are not encrypted or sent to a service.'
          : 'Messages are encrypted on your device. CLIP cannot read them.'}
      </div>
      <KeyStatePanel
        acknowledgedRegistration={acknowledgedRegistration}
        actionBusy={actionBusy}
        keyState={key_state}
        canAcceptChangedKey={Boolean(onAcceptChangedKey)}
        canRegisterKey={Boolean(onAcknowledgeKeyRegistration)}
        onAcceptChangedKey={() => void acceptChangedKey()}
        onAcknowledgeChange={setAcknowledgedRegistration}
        onAcknowledgeKeyRegistration={() => void acknowledgeAndRegister()}
      />
      {refreshError ? (
        <p className="conversation-thread__error" role="status">
          New messages could not be loaded. CLIP will retry while this conversation is open.
        </p>
      ) : null}
      {loading ? <p role="status">Loading messages…</p> : null}
      <ol
        aria-label="Messages"
        aria-live="polite"
        className="conversation-thread__messages"
        ref={messageListRef}
      >
        {entries.map((entry) => (
          <li
            className={
              entry.sender_user_id === current_user_id
                ? 'conversation-thread__message conversation-thread__message--own'
                : 'conversation-thread__message'
            }
            data-sequence={entry.sequence}
            key={entry.entry_id}
          >
            {entry.contact_details ? (
              <section aria-label="Shared contact details" className="conversation-thread__contact-card">
                <p>Contact details shared with you</p>
                {entry.contact_details.email ? <p>Email: <a href={`mailto:${entry.contact_details.email}`}>{entry.contact_details.email}</a></p> : null}
                {entry.contact_details.phone ? <p>Phone: <a href={`tel:${entry.contact_details.phone}`}>{entry.contact_details.phone}</a></p> : null}
                {entry.contact_details.upi_id ? <p>UPI ID: {entry.contact_details.upi_id}</p> : null}
              </section>
            ) : entry.content_deleted || entry.text === null ? (
              <p className="conversation-thread__deleted">{entry.text ?? 'Message content is no longer available.'}</p>
            ) : (
              <p className="conversation-thread__text">{entry.text}</p>
            )}
            {entry.delivery_notice === 'recipient_unable_to_decrypt' ? (
              <p className="conversation-thread__delivery-notice" role="status">
                The recipient couldn’t decrypt this message. You can send it again as a new message.
              </p>
            ) : null}
            <time dateTime={entry.created_at}>{formatMessageTime(entry.created_at)}</time>
          </li>
        ))}
        {pending ? (
          <li aria-live="polite" className="conversation-thread__pending">
            <p>{pending.text}</p>
            {pending.state === 'sending' ? (
              <span>Sending…</span>
            ) : (
              <div className="conversation-thread__retry-row">
                <span role="status">Message not sent.</span>
                <Button disabled={actionBusy} onClick={() => void retry()} variant="secondary">
                  {actionBusy ? 'Retrying…' : 'Retry'}
                </Button>
              </div>
            )}
          </li>
        ) : null}
      </ol>
      {sendError ? (
        <p className="conversation-thread__error" role="status">
          The action did not finish. Retry it or refresh before sending another message.
        </p>
      ) : null}
      <form className="conversation-thread__composer" onSubmit={(event) => void submit(event)}>
        <label htmlFor="conversation-message-draft">Message</label>
        <textarea
          autoComplete="off"
          disabled={!canSend}
          id="conversation-message-draft"
          maxLength={4000}
          onChange={(event) => setDraft(event.currentTarget.value)}
          value={draft}
        />
        <Button disabled={!canSend || !draft.trim()} type="submit">
          {presentationMode === 'local-demo' ? 'Add demo message' : 'Send encrypted message'}
        </Button>
      </form>
    </section>
  );
}

function KeyStatePanel({
  acknowledgedRegistration,
  actionBusy,
  canAcceptChangedKey,
  canRegisterKey,
  keyState,
  onAcceptChangedKey,
  onAcknowledgeChange,
  onAcknowledgeKeyRegistration,
}: {
  acknowledgedRegistration: boolean;
  actionBusy: boolean;
  canAcceptChangedKey: boolean;
  canRegisterKey: boolean;
  keyState: ConversationKeyUiState;
  onAcceptChangedKey: () => void;
  onAcknowledgeChange: (acknowledged: boolean) => void;
  onAcknowledgeKeyRegistration: () => void;
}) {
  if (keyState.kind === 'ready') return null;
  if (keyState.kind === 'waiting_for_peer_key') {
    return <div className="conversation-thread__key-state" role="status">
      <h2>Waiting for the other participant to set up encryption</h2>
      <p>They need to finish their account’s messaging setup before you can send messages. Once set up, they do not need to be online.</p>
      <p>Sending is paused. We’ll check automatically while this page is visible. This is not a conversation acceptance request.</p>
    </div>;
  }
  if (keyState.kind === 'registration_acknowledgement_required') {
    return (
      <div className="conversation-thread__key-state" role="alert">
        <p>{KEY_REGISTRATION_WARNING}</p>
        <label className="conversation-thread__checkbox">
          <input
            checked={acknowledgedRegistration}
            onChange={(event) => onAcknowledgeChange(event.currentTarget.checked)}
            type="checkbox"
          />
          I understand that lost browser key data cannot be restored.
        </label>
        <Button
          disabled={!acknowledgedRegistration || !canRegisterKey || actionBusy}
          onClick={onAcknowledgeKeyRegistration}
        >
          Create encryption key
        </Button>
      </div>
    );
  }
  if (keyState.kind === 'key_change') {
    return (
      <div className="conversation-thread__key-state" role="alert">
        <h2>Encryption key changed</h2>
        <p>{keyState.participant_label} has a new encryption key. Sending is paused.</p>
        <p>{PEER_KEY_CHANGE_WARNING}</p>
        <Button disabled={!canAcceptChangedKey || actionBusy} onClick={onAcceptChangedKey}>
          {actionBusy ? 'Updating trusted key…' : 'Accept new key'}
        </Button>
      </div>
    );
  }
  if (keyState.kind === 'key_state_lost') {
    return (
      <div className="conversation-thread__key-state" role="alert">
        <h2>Encryption key unavailable</h2>
        <p>This browser has lost its encryption key. CLIP cannot restore it; old messages may be unreadable.</p>
      </div>
    );
  }
  return (
    <div className="conversation-thread__key-state" role="alert">
      <p>Encryption is not ready. Sending is paused. Try again later; do not share message contents with support.</p>
    </div>
  );
}

function formatMessageTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString();
}
