import { useMemo, type PropsWithChildren } from 'react';
import { useIdentity } from '../features/identity';
import { ConversationApi, ConversationPageRuntimeProvider, type ListingSelectionPort } from '../features/conversations';
import { ListingsApiError, readOwnedListing, setSelectedListingBuyer,
  type ListingManagementView, type ListingOwnerView } from '../features/listings';
import { sessionFetch } from '../shared/http/sessionFetch';

function toSelectionView(listing: ListingManagementView | ListingOwnerView) {
  return {
    revision: listing.revision,
    availability: listing.availability,
    available_from: listing.available_from,
    available_until: listing.available_until,
    selected_buyer_id: listing.selected_buyer_id ?? null,
    selected_conversation_id: listing.selected_conversation_id ?? null,
  };
}

const listingSelection: ListingSelectionPort = {
  readOwnedListing: async (listingId, signal) => {
    const listing = await readOwnedListing(listingId, signal);
    return toSelectionView(listing);
  },
  selectBuyer: async (listingId, request) => {
    try {
      const listing = await setSelectedListingBuyer(listingId, request);
      return { kind: 'selected', listing: toSelectionView(listing) };
    } catch (error) {
      if (error instanceof ListingsApiError && error.status === 409) return { kind: 'conflict' };
      if (error instanceof ListingsApiError && [401, 403, 404, 422].includes(error.status)) {
        return { kind: 'not_allowed' };
      }
      return { kind: 'dependency' };
    }
  },
};

/** Compose public session state with cookie/CSRF transport. Null unmounts private
 * chat controllers on logout/expiry; same-account session refresh preserves work.
 */
export function ConversationRuntime({ children }: PropsWithChildren) {
  const { status, user } = useIdentity();
  const userId = status === 'ready' && user ? user.user_id : null;
  const runtime = useMemo(() => userId
    ? { userId, api: new ConversationApi(sessionFetch), listingSelection }
    : null, [userId]);
  return <ConversationPageRuntimeProvider runtime={runtime}>{children}</ConversationPageRuntimeProvider>;
}
