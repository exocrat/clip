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

function selectionAllowed(listing: ListingSelectionView, now: number): boolean {
  const startsAt = Date.parse(listing.available_from);
  const endsAt = listing.available_until === null ? Number.POSITIVE_INFINITY : Date.parse(listing.available_until);
  return listing.availability === 'available' && Number.isFinite(startsAt) && startsAt <= now && endsAt > now;
}

/** Seller-only selection UI backed by Listings' serialized owner command. */
export function ConversationListingSelection({ listingId, conversationId, buyerId, selection }: Props) {
  const [listing, setListing] = useState<ListingSelectionView | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [message, setMessage] = useState('');
  const [pendingCommand, setPendingCommand] = useState<SelectionChange | null>(null);
  const activeLoad = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    activeLoad.current?.abort();
    const controller = new AbortController();
    activeLoad.current = controller;
    setLoading(true);
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

  const submit = async () => {
    if (!listing || saving) return;
    const command = pendingCommand ?? {
      buyer_id: buyerId,
      conversation_id: conversationId,
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
        setMessage('Buyer selected. This does not accept an offer or reserve the listing.');
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

  return (
    <section aria-label="Seller buyer selection">
      <h3>Buyer selection</h3>
      {loading ? <p role="status">Checking the listing…</p> : null}
      {loadError ? <div role="alert">
        <p>Couldn’t check the listing’s current state.</p>
        <Button disabled={loading} onClick={() => void refresh()} variant="secondary">Retry listing check</Button>
      </div> : null}
      {!loading && !loadError && listing && selectedForThisBuyer ? <p role="status">This buyer is selected for the listing.</p> : null}
      {!loading && !loadError && listing && !selectedForThisBuyer && !selectionAllowed(listing, Date.now()) ? (
        <p role="status">Buyer selection is available only while the listing is available and within its dates.</p>
      ) : null}
      {!loading && !loadError && listing && !selectedForThisBuyer && selectionAllowed(listing, Date.now()) ? (
        <Button disabled={saving} onClick={() => void submit()}>
          {saving ? 'Selecting…' : pendingCommand ? 'Retry selection' : listing.selected_buyer_id ? 'Select this buyer instead' : 'Select this buyer'}
        </Button>
      ) : null}
      {message ? <p role="status">{message}</p> : null}
      <p>Selecting a buyer is separate from accepting an offer, marking a done deal, or reserving the item.</p>
    </section>
  );
}
