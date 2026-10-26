import type { ReactNode } from 'react';
import { Link } from 'react-router';
import { ListingImagePreview } from '../listings';
import type { ListingSummary } from './discoveryApi';
import { discoveryPrice } from './discoveryApi';
import './discovery.css';

/** One sale-card presentation shared by Discover and the private Saved page. */
export function SaleListingCard({
  listing,
  availabilityLabel,
  children,
}: {
  listing: ListingSummary;
  availabilityLabel?: string;
  children?: ReactNode;
}) {
  return (
    <article className="discovery-card">
      {listing.image_ids[0]
        ? <div className="discovery-card__photo"><ListingImagePreview
            imageId={listing.image_ids[0]}
            alt={`Photo of ${listing.title}`}
            compact
            allowRetry={false}
          /></div>
        : <div className="discovery-card__photo discovery-card__photo--empty" role="img" aria-label={`No photo for ${listing.title}`}>No photo available</div>}
      <p className="discovery-category">{listing.category_label}</p>
      <h2><Link to={`/listings/${listing.listing_id}`}>{listing.title}</Link></h2>
      <p className="discovery-price">{listing.asking_price_paise === 0 ? 'Free' : discoveryPrice(listing.asking_price_paise)}</p>
      <p className="discovery-description">{listing.description}</p>
      <p className="discovery-card-meta">{listing.condition_label} · {listing.negotiable ? 'Negotiable' : 'Fixed price'}</p>
      {listing.pickup_area && <p className="discovery-card-meta">Pickup: {listing.pickup_area}</p>}
      {listing.sensitive_purchase && <p className="discovery-sensitive">Sensitive purchase</p>}
      {availabilityLabel && <p className="discovery-card-meta">{availabilityLabel}</p>}
      <div className="discovery-card__actions">
        {children}
        <Link className="discovery-detail" aria-label={`View ${listing.title}`} to={`/listings/${listing.listing_id}`}>
          View listing <span aria-hidden="true">→</span>
        </Link>
      </div>
    </article>
  );
}
