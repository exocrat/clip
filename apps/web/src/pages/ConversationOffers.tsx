import { useCallback, useEffect, useRef, useState } from 'react';
import type { ConversationSummary, OfferRevisionRequest, OfferView, OfferWithdrawalRequest } from '../../../../contracts/generated/types.gen';
import { ConversationApi } from '../features/conversations';
import { ListingsApiError, submitListingOffer, withdrawListingOffer } from '../features/listings';
import { sessionFetch } from '../shared/http/sessionFetch';
import { Button } from '../shared/ui';
import './ConversationOffers.css';

const api = new ConversationApi(sessionFetch);
type Pending = { kind: 'submit'; body: OfferRevisionRequest } | { kind: 'withdraw'; body: OfferWithdrawalRequest };

/** Route composition connects private offer reads to Listings-owned writes.
 * Only a server-authorized sale conversation exposes this panel. Unknown write
 * outcomes retain the exact operation for explicit retry; conflicts require a
 * fresh read before a new intent. No contact or plaintext note enters an offer.
 */
export function ConversationOffers({ conversationId }: { conversationId: string | undefined }) {
  const [summary, setSummary] = useState<ConversationSummary | null>(null);
  const [offer, setOffer] = useState<OfferView | null>(null);
  const [amount, setAmount] = useState('');
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState<Pending | null>(null);
  const alive = useRef(true);
  const refresh = useCallback(async (signal?: AbortSignal) => {
    if (!conversationId) return;
    const current = await api.readSummary(conversationId, signal);
    if (signal?.aborted) return;
    setSummary(current);
    if (current.origin_kind === 'sale_listing') {
      const response = await sessionFetch(`/conversations/${encodeURIComponent(conversationId)}/offer`, { signal });
      if (!response.ok) throw new Error('Offer unavailable');
      const value: unknown = await response.json();
      if (value !== null && (typeof value !== 'object' || !('amount_paise' in value) ||
        typeof value.amount_paise !== 'number' || !Number.isSafeInteger(value.amount_paise) || value.amount_paise < 0 ||
        !('revision' in value) || typeof value.revision !== 'number' || !Number.isSafeInteger(value.revision) || value.revision < 1 ||
        !('offer_id' in value) || typeof value.offer_id !== 'string' ||
        !('status' in value) || !['submitted', 'withdrawn'].includes(String(value.status)))) throw new Error('Invalid offer');
      if (!signal?.aborted && alive.current) {
        setOffer(value as OfferView | null);
        setAmount(value ? String((value as OfferView).amount_paise / 100) : '');
      }
    }
    if (!signal?.aborted && alive.current) setLoaded(true);
  }, [conversationId]);
  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    void refresh(controller.signal).catch(() => { if (!controller.signal.aborted) setMessage('Couldn’t load the current offer. Refresh to retry.'); });
    return () => { alive.current = false; controller.abort(); };
  }, [refresh]);

  async function write(withdraw = false) {
    if (!summary || !conversationId || busy) return;
    let command = pending;
    if (!command) {
      if (withdraw && offer) command = { kind: 'withdraw', body: { offer_id: offer.offer_id, expected_revision: offer.revision, operation_id: crypto.randomUUID() } };
      else {
        if (!/^\d+$/.test(amount) || Number(amount) > 10000000) { setMessage('Enter a whole-rupee offer from ₹0 to ₹1,00,00,000.'); return; }
        command = { kind: 'submit', body: { amount_paise: Number(amount) * 100, expected_revision: offer?.revision, operation_id: crypto.randomUUID() } };
      }
    }
    setPending(command);
    setBusy(true);
    setMessage('');
    try {
      const result = command.kind === 'submit'
        ? await submitListingOffer(summary.origin_id, conversationId, command.body)
        : await withdrawListingOffer(summary.origin_id, conversationId, command.body);
      if (!alive.current) return;
      setOffer(result);
      setPending(null);
      setMessage(result.status === 'withdrawn' ? 'Offer withdrawn.' : 'Offer submitted. This does not confirm a deal or payment.');
    } catch (error) {
      if (!alive.current) return;
      if (error instanceof ListingsApiError && [401, 403, 404, 409, 422].includes(error.status)) {
        setPending(null);
        setMessage(error.message);
        await refresh().catch(() => setLoaded(false));
      } else setMessage('The offer change could not be confirmed. Retry the same attempt.');
    } finally { if (alive.current) setBusy(false); }
  }

  if (summary?.origin_kind !== 'sale_listing') return message ? <p role="status">{message}</p> : null;
  return <section aria-label="Sale offer" className="conversation-offers">
    <h3>Offer</h3>
    {offer ? <p>₹{(offer.amount_paise / 100).toLocaleString('en-IN')} · {offer.status === 'submitted' ? 'Submitted' : 'Withdrawn'}</p> : <p>No offer yet.</p>}
    {summary.caller_role === 'initiator' && loaded ? <>
      <label className="conversation-offers__amount">Offer amount (₹)<input inputMode="numeric" value={amount} disabled={busy || pending !== null} onChange={(event) => setAmount(event.target.value)} /></label>
      <div className="conversation-offers__actions">
        <Button disabled={busy} onClick={() => void write()}>{busy ? 'Updating…' : pending ? 'Retry offer change' : offer ? 'Update offer' : 'Submit offer'}</Button>
        {offer?.status === 'submitted' && !pending ? <Button variant="secondary" disabled={busy} onClick={() => void write(true)}>Withdraw offer</Button> : null}
      </div>
    </> : null}
    <div className="conversation-offers__actions"><Button disabled={busy || pending !== null} variant="secondary" onClick={() => void refresh().catch(() => setMessage('Couldn’t refresh the offer. Try again.'))}>Refresh offer</Button></div>
    {message ? <p role="status">{message}</p> : null}
  </section>;
}
