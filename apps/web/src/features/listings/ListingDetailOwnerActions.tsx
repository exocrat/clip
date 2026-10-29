import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import { Button } from '../../shared/ui';
import { useIdentity } from '../identity';
import { changeListingAvailability, ListingsApiError, readOwnedListing } from './listingsApi';
import type { ListingManagementView } from './listingsApi';
import { newOperationId } from './operationId';

/** Owner controls appear only after the current session's private list confirms ownership. */
export function ListingDetailOwnerActions({ listingId, onChanged }: {
  listingId: string;
  onChanged: () => void;
}) {
  const { status, user } = useIdentity();
  const eligible = status === 'ready' && user?.account_class === 'regular'
    && Date.parse(user.valid_until) > Date.now();
  return eligible && user
    ? <OwnerActions key={`${user.user_id}:${listingId}`} listingId={listingId} onChanged={onChanged} />
    : null;
}

function OwnerActions({ listingId, onChanged }: { listingId: string; onChanged: () => void }) {
  const [listing, setListing] = useState<ListingManagementView | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  const attempt = useRef<{ intent: string; operationId: string } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setListing(null);
    setError('');
    readOwnedListing(listingId, controller.signal).then((current) => {
      if (!controller.signal.aborted) setListing(current);
    }).catch((failure: Error) => {
      if (controller.signal.aborted) return;
      if (failure instanceof ListingsApiError && (failure.status === 404 || failure.status === 401)) return;
      else {
        setError(failure.message);
      }
    });
    return () => controller.abort();
  }, [listingId, retry]);

  async function toggleAvailability() {
    if (!listing || busy) return;
    const availability = listing.availability === 'available' ? 'unavailable' : 'available';
    const intent = JSON.stringify({
      expected_revision: listing.revision,
      availability,
      available_from: listing.available_from,
      available_until: listing.available_until,
    });
    if (!attempt.current || attempt.current.intent !== intent) {
      attempt.current = { intent, operationId: newOperationId() };
    }
    setBusy(true);
    setError('');
    try {
      await changeListingAvailability(listingId, {
        expected_revision: listing.revision,
        availability,
        available_from: listing.available_from,
        available_until: listing.available_until,
        operation_id: attempt.current.operationId,
      });
      attempt.current = null;
      onChanged();
      setRetry((value) => value + 1);
    } catch (failure) {
      setError((failure as Error).message);
      if (failure instanceof ListingsApiError && failure.status === 409) {
        attempt.current = null;
        setError(`${failure.message} Reload current listing details before retrying.`);
      }
    } finally {
      setBusy(false);
    }
  }

  if (error) return <div className="listings-owner-detail-actions" role="alert">
    <p>{error}</p><Button variant="secondary" onClick={() => setRetry((value) => value + 1)}>Retry owner controls</Button>
  </div>;
  if (!listing) return null;
  return (
    <div className="listings-owner-detail-actions">
      <Link className="ui-button ui-button--secondary" to={`/listings/${encodeURIComponent(listingId)}/edit`}>Edit listing</Link>
      <Button variant="secondary" disabled={busy} onClick={() => void toggleAvailability()}>
        {busy ? 'Saving…' : listing.availability === 'available' ? 'Mark unavailable' : 'Mark available'}
      </Button>
    </div>
  );
}
