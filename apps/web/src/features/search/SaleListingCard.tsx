import type { ReactNode } from 'react';
import { Link } from 'react-router';
import { ListingImagePreview } from '../listings';
import type { ListingSummary } from './discoveryApi';
import { discoveryPrice } from './discoveryApi';
import './discovery.css';

/** Draft fields accepted by the public, non-interactive sale-card preview. */
export type SaleListingPreviewData = {
  title: string;
  description: string;
  categoryLabel: string;
  conditionLabel: string;
  askingPricePaise: number | null;
  originalPricePaise: number | null;
  negotiable: boolean;
  pickupArea: string;
  photoUrl: string | null;
};

type SaleCardViewProps = {
  description: string;
  categoryLabel: string;
  conditionLabel: string;
  askingPricePaise: number | null;
  originalPricePaise: number | null;
  negotiable: boolean;
  pickupArea?: string | null;
  image: ReactNode;
  titleContent: ReactNode;
  actions?: ReactNode;
  availabilityLabel?: string;
  sensitivePurchase?: boolean;
};

/** Shared markup keeps the browse card and draft preview visually in sync. */
function SaleCardView({
  description, categoryLabel, conditionLabel, askingPricePaise, originalPricePaise, negotiable,
  pickupArea, image, titleContent, actions, availabilityLabel, sensitivePurchase = false,
}: SaleCardViewProps) {
  return (
    <article className="discovery-card">
      {image}
      <p className="discovery-category">{categoryLabel || 'Choose a category'}</p>
      <h2>{titleContent}</h2>
      <p className="discovery-price">
        {askingPricePaise === null ? 'Add a price' : askingPricePaise === 0 ? 'Free' : discoveryPrice(askingPricePaise)}
      </p>
      {originalPricePaise !== null && <p className="discovery-card-meta">Original price (seller-provided, unverified): {discoveryPrice(originalPricePaise)}</p>}
      <p className="discovery-negotiability">{negotiable ? 'Negotiable' : 'Fixed price'}</p>
      <p className="discovery-description">{description || 'Add a description'}</p>
      <p className="discovery-card-meta">Condition: {conditionLabel || 'Choose a condition'}</p>
      {pickupArea && <p className="discovery-card-meta">Pickup: {pickupArea}</p>}
      {sensitivePurchase && <p className="discovery-sensitive">Sensitive purchase</p>}
      {availabilityLabel && <p className="discovery-card-meta">{availabilityLabel}</p>}
      {actions ? <div className="discovery-card__actions">{actions}</div> : null}
    </article>
  );
}

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
    <SaleCardView
      description={listing.description}
      categoryLabel={listing.category_label}
      conditionLabel={listing.condition_label}
      askingPricePaise={listing.asking_price_paise}
      originalPricePaise={listing.original_price_paise}
      negotiable={listing.negotiable}
      pickupArea={listing.pickup_area}
      sensitivePurchase={listing.sensitive_purchase}
      availabilityLabel={availabilityLabel}
      image={listing.image_ids[0]
        ? <div className="discovery-card__photo"><ListingImagePreview
            imageId={listing.image_ids[0]}
            alt={`Photo of ${listing.title}`}
            compact
            allowRetry={false}
          /></div>
        : <div className="discovery-card__photo discovery-card__photo--empty" role="img" aria-label={`No photo for ${listing.title}`}>No photo available</div>}
      titleContent={<Link to={`/listings/${listing.listing_id}`}>{listing.title}</Link>}
      actions={<>
        {children}
        <Link className="discovery-detail" aria-label={`View ${listing.title}`} to={`/listings/${listing.listing_id}`}>
          View listing <span aria-hidden="true">→</span>
        </Link>
      </>}
    />
  );
}

/** Render the current unsaved draft with the exact card layout used in browse. */
export function SaleListingPreview({ draft }: { draft: SaleListingPreviewData }) {
  return (
    <SaleCardView
      description={draft.description}
      categoryLabel={draft.categoryLabel}
      conditionLabel={draft.conditionLabel}
      askingPricePaise={draft.askingPricePaise}
      originalPricePaise={draft.originalPricePaise}
      negotiable={draft.negotiable}
      pickupArea={draft.pickupArea}
      image={draft.photoUrl
        ? <div className="discovery-card__photo"><img src={draft.photoUrl} alt={draft.title ? `Photo of ${draft.title}` : 'Listing photo preview'} /></div>
        : <div className="discovery-card__photo discovery-card__photo--empty" role="img" aria-label="No photo selected">No photo selected</div>}
      titleContent={draft.title || 'Add a title'}
    />
  );
}
