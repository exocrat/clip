import { isolatedListingsDemo, publicListingsDemo } from './listingsApi';

/** Explain the platform's limits and label the separate local synthetic demo. */
export function ListingNotice() {
  return (
    <>
      {(isolatedListingsDemo || publicListingsDemo) && (
        <aside className="listings-demo" aria-label="Listings test mode">
          <strong>
            {publicListingsDemo
              ? 'Isolated Listings demo — synthetic seller and data'
              : 'Local Listings test — synthetic seller'}
          </strong>
          <p>
            {publicListingsDemo
              ? 'This public rehearsal uses a fixed synthetic seller. Do not enter real personal information or upload real personal photos.'
              : 'This local test uses a synthetic seller supplied by the local test server.'}
          </p>
        </aside>
      )}
      <p className="listings-muted">
        CLIP does not verify payment, item quality, collection, delivery or handover.
        Item condition and proof availability are unverified seller statements.
      </p>
    </>
  );
}
