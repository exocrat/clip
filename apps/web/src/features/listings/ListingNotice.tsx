import { isolatedListingsDemo } from './listingsApi';

/** Explain the platform's limits and label the separate local synthetic demo. */
export function ListingNotice() {
  return (
    <>
      {isolatedListingsDemo && (
        <aside className="listings-demo" aria-label="Local test mode">
          <strong>Isolated Listings test — synthetic seller</strong>
          <p>Listings save to real local PostgreSQL. Sign-in and image records are synthetic.
            No photo has been uploaded. Real Identity, image storage and chat are pending.</p>
        </aside>
      )}
      <p className="listings-muted">
        CLIP does not verify payment, item quality, collection, delivery or handover.
        Item condition and proof availability are unverified seller statements.
      </p>
    </>
  );
}
