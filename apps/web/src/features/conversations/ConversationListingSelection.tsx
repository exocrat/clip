import { useCallback, useEffect, useRef, useState } from 'react';
import type { ConversationSummary, SelectionChange } from '../../../../../contracts/generated/types.gen';
import { Button } from '../../shared/ui';

export type ListingSelectionView = {
  revision: number;
  availability: 'available' | 'unavailable';
  available_from: string;
  available_until: string | null;
  selected_buyer_id: string | null;
  selected_conversation_id: string | null;
};

export type ListingSelectionAttempt =
  | { kind: 'selected'; listing: ListingSelectionView }
  | { kind: 'conflict' | 'not_allowed' | 'dependency' };

/** Narrow page-composition port: Conversations never imports Listings internals. */
export type ListingSelectionPort = {
  readOwnedListing: (listingId: string, signal: AbortSignal) => Promise<ListingSelectionView>;
  selectBuyer: (listingId: string, request: SelectionChange) => Promise<ListingSelectionAttempt>;
};

/** Only a verified seller for a Sale Listing conversation may get this control. */
export function isSellerSaleListingConversation(
  summary: Pick<ConversationSummary, 'caller_role' | 'origin_kind'>,
): boolean {
  return summary.caller_role === 'origin_owner' && summary.origin_kind === 'sale_listing';
}

type Props = {
  listingId: string;
  conversationId: string;
  buyerId: string;
  selection: ListingSelectionPort;
};

/** Seller-only selection UI backed by Listings' serialized owner command. */
export function ConversationListingSelection({ listingId, conversationId, buyerId, selection }: Props) {
  const [listing, setListing] = useState<ListingSelectionView | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [message, setMessage] = useState('');
  const [pendingCommand, setPendingCommand] = useState<SelectionChange | null>(null);
  const activeLoad = useRef<AbortController | null>(null);

  const refresh = useCallback(async (silent = false) => {
    activeLoad.current?.abort();
    const controller = new AbortController();
    activeLoad.current = controller;
    if (!silent) setLoading(true);
    setLoadError(false);
    try {
      const current = await selection.readOwnedListing(listingId, controller.signal);
      if (!controller.signal.aborted) setListing(current);
      return true;
    } catch {
      if (!controller.signal.aborted) setLoadError(true);
      return false;
    } finally {
      if (activeLoad.current === controller) {
        activeLoad.current = null;
        setLoading(false);
      }
    }
  }, [listingId, selection]);

  useEffect(() => {
    void refresh();
    return () => {
      activeLoad.current?.abort();
      activeLoad.current = null;
    };
  }, [refresh]);

  // Another page may reopen or select this listing. Refresh visible state without
  // discarding the exact command after an uncertain write.
  useEffect(() => {
    const update = () => { if (document.visibilityState === 'visible' && !(saving || pendingCommand)) void refresh(true); };
    const timer = setInterval(update, 2000);
    window.addEventListener('focus', update);
    document.addEventListener('visibilitychange', update);
    return () => { clearInterval(timer); window.removeEventListener('focus', update); document.removeEventListener('visibilitychange', update); };
  }, [refresh, saving, pendingCommand]);

  const submit = async (clear = false) => {
    if (!listing || saving) return;
    const command = pendingCommand ?? {
      buyer_id: clear ? null : buyerId,
      conversation_id: clear ? null : conversationId,
      expected_revision: listing.revision,
      operation_id: crypto.randomUUID(),
    };
    setPendingCommand(command);
    setSaving(true);
    setMessage('');
    try {
      const result = await selection.selectBuyer(listingId, command);
      if (result.kind === 'selected') {
        setListing(result.listing);
        setPendingCommand(null);
        setMessage(command.buyer_id ? 'Buyer selected for your private tracking. Availability is unchanged.' : 'Buyer selection cleared. Availability is unchanged.');
      } else if (result.kind === 'conflict') {
        setPendingCommand(null);
        await refresh();
        setMessage('The listing changed. Its latest state is loaded; select again if buyer selection is still available.');
      } else if (result.kind === 'not_allowed') {
        setPendingCommand(null);
        setMessage('Buyer selection is not allowed for the current listing or account state.');
      } else {
        // Keep the exact request and operation ID: a timeout may have happened
        // after Listings committed, so retrying a new command would be unsafe.
        setMessage('Selection could not be confirmed. Retry this same attempt.');
      }
    } catch {
      setMessage('Selection could not be confirmed. Retry this same attempt.');
    } finally {
      setSaving(false);
    }
  };

  const selectedForThisBuyer = listing?.selected_buyer_id === buyerId &&
    listing.selected_conversation_id === conversationId;
  const selectionComplete = selectedForThisBuyer;

  return (
    <section aria-label="Seller buyer selection">
      <h3>Buyer selection</h3>
      {loading ? <p role="status">Checking the listing…</p> : null}
      {loadError ? <div role="alert">
        <p>Couldn’t check the listing’s current state.</p>
        <Button disabled={loading} onClick={() => void refresh()} variant="secondary">Retry listing check</Button>
      </div> : null}
      {!loading && !loadError && listing && selectedForThisBuyer ? <p role="status">
        This buyer is selected for your private tracking.
      </p> : null}
      {!loading && !loadError && listing && !selectionComplete ? (
        <Button disabled={saving} onClick={() => void submit()}>
          {saving ? 'Selecting…' : pendingCommand ? 'Retry selection' : listing.selected_buyer_id && !selectedForThisBuyer ? 'Select this buyer instead' : 'Select this buyer'}
        </Button>
      ) : null}
      {!loading && !loadError && listing?.selected_buyer_id ? <Button disabled={saving} variant="secondary" onClick={() => void submit(true)}>Clear selected buyer</Button> : null}
      {message ? <p role="status">{message}</p> : null}
      <p>Selection is private to you and leaves availability unchanged. Mark as done deal separately when the listing should become unavailable.</p>
    </section>
  );
}
