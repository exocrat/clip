import { isolatedListingsDemo } from './listingsApi';

/** Explain the platform's limits and label the separate local synthetic demo. */
export function ListingNotice() {
  return (
    <>
      {isolatedListingsDemo && (
        <aside className="listings-demo" aria-label="Local test mode">
          <strong>Isolated Listings test — synthetic seller</strong>
          <p>This development mode uses a synthetic seller supplied by the separate local test server. Image storage availability depends on that server. Real sign-in, cloud storage verification, and chat integration remain pending.</p>
        </aside>
      )}
      <p className="listings-muted">
        CLIP does not verify payment, item quality, collection, delivery or handover.
        Item condition and proof availability are unverified seller statements.
      </p>
    </>
  );
}
