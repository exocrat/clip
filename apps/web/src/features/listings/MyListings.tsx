import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router';
import { Button } from '../../shared/ui';
import { ListingNotice } from './ListingNotice';
import { ListingImagePreview } from './ListingImagePreview';
import { ListingPhotoPlaceholder } from './ListingPhotoPlaceholder';
import {
  changeListingAvailability,
  listingPrice,
  ListingsApiError,
  readMyListings,
  type AvailabilityChange,
  type ListingManagementView,
} from './listingsApi';
import { newOperationId } from './operationId';
import './listings.css';

type AvailabilityFilter = 'all' | 'available' | 'unavailable';
type AvailabilityAttempt = { intent: string; body: AvailabilityChange };

/** Show and manage this signed-in seller's listings through the owner-only API. */
export function MyListings() {
  const [pages, setPages] = useState<Record<number, ListingManagementView[]>>({});
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [filter, setFilter] = useState<AvailabilityFilter>('all');
  const [error, setError] = useState('');
  const [availabilityError, setAvailabilityError] = useState('');
  const [availabilitySuccess, setAvailabilitySuccess] = useState('');
  const [reloadRequired, setReloadRequired] = useState(false);
  const [busyListing, setBusyListing] = useState('');
  const [loading, setLoading] = useState(false);
  const [retry, setRetry] = useState(0);
  const attempts = useRef(new Map<string, AvailabilityAttempt>());

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    if (filter !== 'all') setPages({});

    async function loadListings() {
      try {
        if (filter === 'all') {
          const result = await readMyListings(page, controller.signal);
          if (controller.signal.aborted) return;
          setPages((current) => ({ ...current, [page]: result.items }));
          setHasNext(result.has_next);
          return;
        }

        // Status views include every owner listing, even when it spans pages.
        const loaded: Record<number, ListingManagementView[]> = {};
        for (let nextPage = 1; ; nextPage += 1) {
          const result = await readMyListings(nextPage, controller.signal);
          if (controller.signal.aborted) return;
          loaded[nextPage] = result.items;
          setPages({ ...loaded });
          if (!result.has_next) break;
        }
        setHasNext(false);
      } catch (failure) {
        if (!controller.signal.aborted) setError((failure as Error).message);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void loadListings();
    return () => controller.abort();
  }, [filter, page, retry]);

  const listings = useMemo(
    () => Object.keys(pages).map(Number).sort((left, right) => left - right).flatMap((key) => pages[key] ?? []),
    [pages],
  );
  const visibleListings = filter === 'all'
    ? listings
    : listings.filter((listing) => listing.availability === filter);
  const loadedCurrentPage = Object.hasOwn(pages, page);

  function changeFilter(nextFilter: AvailabilityFilter) {
    setFilter(nextFilter);
    setPage(1);
    setPages({});
    setHasNext(false);
    setError('');
    setAvailabilityError('');
    setAvailabilitySuccess('');
    setReloadRequired(false);
  }

  function reloadListings() {
    setPage(1);
    setPages({});
    setHasNext(false);
    setError('');
    setAvailabilityError('');
    setReloadRequired(false);
    setRetry((value) => value + 1);
  }

  async function toggleAvailability(listing: ListingManagementView) {
    if (busyListing || reloadRequired) return;
    const availability = listing.availability === 'available' ? 'unavailable' : 'available';
    const key = `${listing.listing_id}:${availability}`;
    const intent = JSON.stringify({
      expected_revision: listing.revision,
      availability,
      available_from: listing.available_from,
      available_until: listing.available_until,
    });
    let attempt = attempts.current.get(key);
    if (!attempt || attempt.intent !== intent) {
      attempt = {
        intent,
        body: {
          expected_revision: listing.revision,
          availability,
          available_from: listing.available_from,
          available_until: listing.available_until,
          operation_id: newOperationId(),
        },
      };
      attempts.current.set(key, attempt);
    }

    setBusyListing(listing.listing_id);
    setAvailabilityError('');
    setAvailabilitySuccess('');
    try {
      await changeListingAvailability(listing.listing_id, attempt.body);
      attempts.current.delete(key);
      setAvailabilitySuccess(`“${listing.title}” is now marked ${availability}.`);
      reloadListings();
    } catch (failure) {
      const apiFailure = failure instanceof ListingsApiError ? failure : null;
      setAvailabilityError((failure as Error).message);
      if (apiFailure?.status === 409) {
        attempts.current.delete(key);
        setReloadRequired(true);
      }
    } finally {
      setBusyListing('');
    }
  }

  return (
    <section className="listings-feature">
      <ListingNotice />
      <p>Listings you created with this account appear here.</p>
      <div className="listings-filter">
        <label htmlFor="my-listings-availability">Show</label>
        <select
          id="my-listings-availability"
          value={filter}
          onChange={(event) => changeFilter(event.target.value as AvailabilityFilter)}
        >
          <option value="all">All listings</option>
          <option value="available">Available listings</option>
          <option value="unavailable">Unavailable listings</option>
        </select>
      </div>
      {error ? (
        <div role="alert">
          <p>{error}</p>
          <Button onClick={reloadListings}>
            {loadedCurrentPage ? 'Retry loading listings' : 'Try loading listings again'}
          </Button>
        </div>
      ) : null}
      {availabilityError ? (
        <div role="alert" className="listings-alert">
          <p>{availabilityError}</p>
          {reloadRequired ? (
            <Button variant="secondary" onClick={reloadListings}>Reload latest listings</Button>
          ) : <p>Retry the same action to safely retry this update.</p>}
        </div>
      ) : null}
      {availabilitySuccess ? <p role="status">{availabilitySuccess}</p> : null}
      {loading && listings.length === 0 ? (
        <p role="status">{filter === 'all' ? 'Loading your listings…' : `Loading all ${filter} listings…`}</p>
      ) : null}
      {!loading && !error && listings.length === 0 && filter === 'all' ? (
        <div className="listings-empty">
          <p>You haven’t published a sale listing yet.</p>
          <Link to="/listings/new">Create a listing</Link>
        </div>
      ) : null}
      {!loading && !error && listings.length > 0 && visibleListings.length === 0 ? (
        <p className="listings-empty">
          {filter === 'available' ? 'You have no available listings.' : 'You have no unavailable listings.'}
        </p>
      ) : null}
      {visibleListings.length > 0 ? (
        <ul className="listings-list">
          {visibleListings.map((listing) => (
            <li className="listings-list-card" key={listing.listing_id}>
              <figure className="listings-list-photo" aria-label={`Photo preview for ${listing.title}`}>
                {listing.image_ids[0]
                  ? <ListingImagePreview imageId={listing.image_ids[0]} alt={`First photo of ${listing.title}`} compact />
                  : <ListingPhotoPlaceholder compact />}
              </figure>
              <div>
                <p className="listings-status">
                  {listing.availability === 'available' ? 'Available' : 'Unavailable'}
                </p>
                <h2><Link to={`/listings/${encodeURIComponent(listing.listing_id)}`}>{listing.title}</Link></h2>
                <p className="listings-price">
                  {listingPrice(listing.asking_price_paise)}
                  {listing.negotiable ? ' · Negotiable' : ' · Fixed asking price'}
                </p>
                <p>{listing.category_label} · {listing.condition_label}</p>
                <p className="listings-muted">{listing.image_ids.length} photo{listing.image_ids.length === 1 ? '' : 's'}</p>
                <p className="listings-muted">
                  Updated {new Date(listing.updated_at).toLocaleDateString()}
                </p>
              </div>
              <div className="listings-list-card__links">
                <Link to={`/listings/${encodeURIComponent(listing.listing_id)}/edit`}>Edit listing</Link>
                <Link to={`/listings/${encodeURIComponent(listing.listing_id)}`}>View listing</Link>
                <Button
                  variant="secondary"
                  disabled={busyListing !== '' || reloadRequired}
                  onClick={() => void toggleAvailability(listing)}
                >
                  {busyListing === listing.listing_id
                    ? 'Saving…'
                    : listing.availability === 'available' ? 'Mark unavailable' : 'Mark available'}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
      {loading && listings.length > 0 ? <p role="status">Loading listings…</p> : null}
      {!error && filter === 'all' && hasNext ? (
        <Button disabled={loading} onClick={() => setPage((current) => current + 1)}>
          Show more listings
        </Button>
      ) : null}
    </section>
  );
}
