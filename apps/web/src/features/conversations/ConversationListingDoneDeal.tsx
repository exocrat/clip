import { useCallback, useEffect, useRef, useState } from 'react';
import type { AvailabilityChange } from '../../../../../contracts/generated/types.gen';
import { Button } from '../../shared/ui';
import type { ListingSelectionView } from './ConversationListingSelection';

/** Listings owns both the mutation and refreshed owner-only state. */
export type ListingAvailabilityPort = {
  readOwnedListing: (listingId: string, signal: AbortSignal) => Promise<ListingSelectionView>;
  markUnavailable: (listingId: string, request: AvailabilityChange) => Promise<
    { kind: 'done'; listing: ListingSelectionView } |
    { kind: 'conflict' | 'not_allowed' | 'dependency' }
  >;
};

/** Owner-only group action; ambiguous writes keep their exact operation for retry. */
export function ConversationListingDoneDeal({ listingId, availability }: {
  listingId: string; availability: ListingAvailabilityPort;
}) {
  const [listing, setListing] = useState<ListingSelectionView | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [message, setMessage] = useState('');
  const pending = useRef<AvailabilityChange | null>(null);
  const alive = useRef(true);
  const readController = useRef<AbortController | null>(null);
  const refresh = useCallback(async () => {
    readController.current?.abort();
    const controller = new AbortController();
    readController.current = controller;
    setLoading(true);
    setLoadError(false);
    try {
      const current = await availability.readOwnedListing(listingId, controller.signal);
      if (!controller.signal.aborted) setListing(current);
    } catch {
      if (!controller.signal.aborted) setLoadError(true);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [availability, listingId]);
  useEffect(() => {
    alive.current = true;
    void refresh();
    return () => { alive.current = false; readController.current?.abort(); };
  }, [refresh]);

  async function markDone() {
    if (!listing || busy) return;
    const request = pending.current ?? {
      expected_revision: listing.revision,
      availability: 'unavailable' as const,
      available_from: listing.available_from,
      // Null/omission clears the end date in this API; retain the actual value.
      available_until: listing.available_until,
      operation_id: crypto.randomUUID(),
    };
    pending.current = request;
    setBusy(true);
    setMessage('');
    try {
      const result = await availability.markUnavailable(listingId, request);
      if (!alive.current) return;
      if (result.kind === 'done') {
        setListing(result.listing);
        pending.current = null;
        setMessage(result.listing.availability === 'unavailable'
          ? 'Listing marked unavailable. Existing conversations remain open.'
          : 'The listing was updated again and is currently available.');
      } else if (result.kind === 'conflict') {
        pending.current = null;
        await refresh();
        if (alive.current) setMessage('The listing changed. Review its current state before trying again.');
      } else if (result.kind === 'not_allowed') {
        pending.current = null;
        setMessage('This action is not allowed for the current listing or account.');
      } else {
        setMessage('The change could not be confirmed. Retry the same attempt.');
      }
    } catch {
      if (alive.current) setMessage('The change could not be confirmed. Retry the same attempt.');
    } finally {
      if (alive.current) setBusy(false);
    }
  }

  return <div>
    {loading ? <span role="status">Checking listing availability…</span> : loadError ? <>
      <span role="alert">Couldn’t check listing availability.</span>
      <Button onClick={() => void refresh()} variant="secondary">Retry listing check</Button>
    </> : listing?.availability === 'unavailable' ? <span role="status">Listing unavailable</span> : listing ?
      <Button disabled={busy} onClick={() => void markDone()}>
        {busy ? 'Updating…' : pending.current ? 'Retry marking unavailable' : 'Mark as done deal'}
      </Button> : null}
    {message ? <p role="status">{message}</p> : null}
  </div>;
}
