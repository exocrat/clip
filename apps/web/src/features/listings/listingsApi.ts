import type {
  CatalogueView,
  ConfirmedImage,
  CreateListingRequest,
  ListingDetail,
  ListingManagementView,
  ListingReplacement,
  PageResultListingManagementView,
} from '../../../../../contracts/generated/types.gen';

export type {
  CatalogueView,
  ConfirmedImage,
  CreateListingRequest,
  ListingDetail,
  ListingManagementView,
  ListingReplacement,
  PageResultListingManagementView,
};

/** Test controls are compiled out of the production build. Auth stays server-owned. */
export const isolatedListingsDemo =
  import.meta.env.DEV && import.meta.env.VITE_LISTINGS_ISOLATED_DEMO === 'true';

/** Keep failures actionable without reflecting raw API/provider diagnostics. */
export class ListingsApiError extends Error {
  constructor(public readonly status: number) {
    const messages: Record<number, string> = {
      401: 'Your session is missing or expired. Sign in again before continuing.',
      403: 'This account is not allowed to perform this action.',
      404: 'This listing is missing or is not available to this account.',
      409: 'The listing or request has changed. Reload its current state before continuing.',
      422: 'Some details were rejected. Check the fields, dates and confirmed images.',
      503: 'A required service is unavailable. Your form has been kept; try again later.',
    };
    super(messages[status] ?? 'The request could not be completed. Please try again.');
  }
}

/** Call the same-origin API; writes have no automatic retry or client actor ID. */
export async function listingsRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      credentials: 'same-origin',
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ListingsApiError(0);
  }
  if (!response.ok) throw new ListingsApiError(response.status);
  try {
    return await response.json() as T;
  } catch {
    // Malformed responses must not surface raw response content in the page.
    throw new ListingsApiError(0);
  }
}

export const readCatalogue = (signal: AbortSignal) =>
  listingsRequest<CatalogueView>('/catalogue', { signal });

export const readListing = (listingId: string, signal: AbortSignal) =>
  listingsRequest<ListingDetail>(`/listings/${encodeURIComponent(listingId)}`, { signal });

/** The server resolves the current account and returns only its management rows. */
export const readMyListings = (
  page: number,
  signal: AbortSignal,
) => listingsRequest<PageResultListingManagementView>(
  `/me/listings?page=${page}`,
  { signal },
);

/** Find one fresh owner-only record through the existing bounded page contract. */
export async function readOwnedListing(listingId: string, signal: AbortSignal) {
  for (let page = 1; ; page += 1) {
    const result = await readMyListings(page, signal);
    const listing = result.items.find((item) => item.listing_id === listingId);
    if (listing) return listing;
    if (!result.has_next) throw new ListingsApiError(404);
  }
}

export const createListing = (body: CreateListingRequest) =>
  listingsRequest<ListingDetail>('/listings', { method: 'POST', body: JSON.stringify(body) });

export const replaceListing = (listingId: string, body: ListingReplacement) =>
  listingsRequest<ListingDetail>(`/listings/${encodeURIComponent(listingId)}`, {
    method: 'PUT', body: JSON.stringify(body),
  });

/** Prepare metadata only through the separate test app; never emulate an upload. */
export function prepareDemoImage(): Promise<ConfirmedImage> {
  if (!isolatedListingsDemo) throw new Error('Isolated Listings mode is required');
  return listingsRequest<ConfirmedImage>('/__listings_demo/image', { method: 'POST' });
}

/** Format integer paise for display without altering stored money. */
export function listingPrice(paise: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0,
  }).format(paise / 100);
}
