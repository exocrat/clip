import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router';
import { Button } from '../../shared/ui';
import { ListingNotice } from './ListingNotice';
import { ListingPhotoPlaceholder } from './ListingPhotoPlaceholder';
import { listingPrice, readMyListings, type ListingManagementView } from './listingsApi';
import './listings.css';

/** Show this signed-in seller's own saved listings from the owner-only API. */
export function MyListings() {
  const [pages, setPages] = useState<Record<number, ListingManagementView[]>>({});
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    readMyListings(page, controller.signal).then((result) => {
      if (controller.signal.aborted) return;
      setPages((current) => ({ ...current, [page]: result.items }));
      setHasNext(result.has_next);
    }).catch((failure: Error) => {
      if (!controller.signal.aborted) setError(failure.message);
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [page, retry]);

  const listings = useMemo(
    () => Object.keys(pages).map(Number).sort((left, right) => left - right).flatMap((key) => pages[key] ?? []),
    [pages],
  );
  const loadedCurrentPage = Object.hasOwn(pages, page);

  return (
    <section className="listings-feature">
      <ListingNotice />
      <p>Listings you created with this account appear here.</p>
      {error ? (
        <div role="alert">
          <p>{error}</p>
          <Button onClick={() => setRetry((value) => value + 1)}>
            {loadedCurrentPage ? 'Retry loading listings' : 'Try loading listings again'}
          </Button>
        </div>
      ) : null}
      {loading && listings.length === 0 ? <p role="status">Loading your listings…</p> : null}
      {!loading && !error && listings.length === 0 ? (
        <div className="listings-empty">
          <p>You haven’t published a sale listing yet.</p>
          <Link to="/listings/new">Create a listing</Link>
        </div>
      ) : null}
      {listings.length > 0 ? (
        <ul className="listings-list">
          {listings.map((listing) => (
            <li className="listings-list-card" key={listing.listing_id}>
              <figure className="listings-list-photo" aria-label={`Photo preview for ${listing.title}`}>
                <ListingPhotoPlaceholder compact />
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
              </div>
            </li>
          ))}
        </ul>
      ) : null}
      {loading && listings.length > 0 ? <p role="status">Loading more listings…</p> : null}
      {!error && hasNext ? (
        <Button disabled={loading} onClick={() => setPage((current) => current + 1)}>
          Show more listings
        </Button>
      ) : null}
    </section>
  );
}
