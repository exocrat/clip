import { useEffect, useState, type PropsWithChildren } from 'react';
import { Link, useLocation } from 'react-router';
import { Button } from '../../shared/ui';
import { ListingNotice } from './ListingNotice';
import { ListingPhotoGallery } from './ListingPhotoGallery';
import { listingPrice, readListing, type ListingDetail as Detail } from './listingsApi';
import './listings.css';

/** Fetch saved detail afresh on navigation/reload; never treat route IDs as authority. */
export function ListingDetail({ listingId, children }: PropsWithChildren<{ listingId?: string }>) {
  const [listing, setListing] = useState<Detail | null>(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const location = useLocation();
  const validId = Boolean(listingId && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(listingId));

  useEffect(() => {
    const controller = new AbortController();
    setListing(null);
    setError('');
    if (validId && listingId) {
      readListing(listingId, controller.signal).then((result) => {
        if (!controller.signal.aborted) setListing(result);
      }).catch((failure: Error) => {
        if (!controller.signal.aborted) setError(failure.message);
      });
    }
    return () => controller.abort();
  }, [listingId, validId, retry]);

  return (
    <section className="listings-feature">
      <ListingNotice />
      {!validId ? <p role="alert">We couldn’t find that listing. Check the link and try again.</p>
        : error ? <div role="alert"><p>{error}</p><Button onClick={() => setRetry((value) => value + 1)}>Retry loading listing</Button></div>
          : !listing ? <p role="status">Loading saved listing…</p> : (
            <article className="listings-card">
              {location.state?.listingCreated && <p role="status">Your listing has been published.</p>}
              {location.state?.listingUpdated && <p role="status">Your listing changes have been saved.</p>}
              <p className="listings-status">{listing.availability === 'available' ? 'Seller marked available' : 'Seller marked unavailable'}</p>
              <h2>{listing.title}</h2>
              <p className="listings-price">{listingPrice(listing.asking_price_paise)}{listing.negotiable ? ' · Negotiable' : ' · Fixed asking price'}</p>
              {listing.original_price_paise !== null && <p>Original price (seller-provided, unverified): {listingPrice(listing.original_price_paise)}</p>}
              <ListingPhotoGallery imageIds={listing.image_ids} />
              <p className="listings-description">{listing.description}</p>
              <dl>
                <dt>Item category</dt><dd>{listing.category_label}</dd>
                <dt>Condition (seller stated)</dt><dd>{listing.condition_label}</dd>
                <dt>Pickup area</dt><dd>{listing.pickup_area ?? 'Not specified'}</dd>
                <dt>Available from</dt><dd>{new Date(listing.available_from).toLocaleString()}</dd>
                <dt>Available until</dt><dd>{listing.available_until ? new Date(listing.available_until).toLocaleString() : 'No end date stated'}</dd>
                <dt>Proof of purchase (unverified)</dt><dd>{listing.proof_available === null ? 'Not stated' : listing.proof_available ? 'Seller says available' : 'Seller says unavailable'}</dd>
              </dl>
              {listing.sensitive_purchase && <p className="listings-alert">Sensitive purchase: this item is flagged by its category or asking price. Check its details and any proof directly with the seller.</p>}
              <p className="listings-id">Listing ID: <code>{listing.listing_id}</code></p>
              <Link to="/listings/new">Create another listing</Link>
              {children}
            </article>
          )}
    </section>
  );
}
