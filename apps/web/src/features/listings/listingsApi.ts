import { sessionFetch, SessionFetchError } from '../../shared/http/sessionFetch';
import { batchedRead } from '../../shared/http/batchedRead';
import type {
  OfferRevisionRequest,
  OfferWithdrawalRequest,
  OfferView,
  AvailabilityChange,
  CatalogueView,
  ConfirmedImage,
  CreateListingRequest,
  ListingDetail,
  ListingManagementView,
  ListingReplacement,
  PageResultListingManagementView,
  ImageDelivery,
  ImageDeliveryBatch,
  ImageUploadRequest,
  ListingOwnerView,
  SelectionChange,
  UploadInstruction,
} from '../../../../../contracts/generated/types.gen';

export type {
  AvailabilityChange,
  CatalogueView,
  ConfirmedImage,
  CreateListingRequest,
  ListingDetail,
  ListingManagementView,
  ListingReplacement,
  PageResultListingManagementView,
  ImageUploadRequest,
  ListingOwnerView,
  SelectionChange,
  UploadInstruction,
};

/** The synthetic browser helpers remain development-only; auth stays server-owned. */
export const publicListingsDemo = import.meta.env.VITE_LISTINGS_PUBLIC_DEMO === 'true';
export const isolatedListingsDemo =
  import.meta.env.DEV && import.meta.env.VITE_LISTINGS_ISOLATED_DEMO === 'true';

/** Keep failures actionable without reflecting raw API/provider diagnostics. */
export class ListingsApiError extends Error {
  constructor(public readonly status: number, code?: string) {
    const messages: Record<number, string> = {
      401: 'Your session is missing or expired. Sign in again before continuing.',
      403: 'This account is not allowed to perform this action.',
      404: 'This listing is missing or is not available to this account.',
      409: 'The listing or request has changed. Reload its current state before continuing.',
      422: 'Use a title up to 120 characters, description up to 5,000, and pickup area up to 120; enter whole-rupee prices up to ₹1,00,00,000 and check dates and photos.',
      503: 'A required service is unavailable. Your form has been kept; try again later.',
    };
    super(code === 'demo_listing_limit_reached'
      ? 'This isolated demo has reached its ten-listing limit. Stop and restart it to begin a fresh run.'
      : messages[status] ?? 'The request could not be completed. Please try again.');
  }
}

export class ListingImageFinalError extends Error {}

/** Use Listings' owner-state gate; return only a validated conversation target. */
export async function startListingConversation(listingId: string, operationId: string, signal: AbortSignal) {
  const value: unknown = await listingsRequest(`/listings/${encodeURIComponent(listingId)}/conversations`, {
    method: 'POST', body: JSON.stringify({ operation_id: operationId }), signal,
  });
  if (!value || typeof value !== 'object' || Object.keys(value).length !== 2 ||
    !('created' in value) || typeof value.created !== 'boolean' || !('conversation_id' in value) ||
    typeof value.conversation_id !== 'string' ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value.conversation_id)) {
    throw new ListingsApiError(503);
  }
  return { conversation_id: value.conversation_id, created: value.created };
}

/** Call the same-origin API; writes have no automatic retry or client actor ID. */
export async function listingsRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    const headers = new Headers(options.headers);
    if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
    response = await sessionFetch(path, { ...options, headers });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ListingsApiError(error instanceof SessionFetchError ? error.status : 0);
  }
  if (!response.ok) {
    let code: string | undefined;
    try {
      const payload = await response.json() as {
        error?: { details?: Array<{ code?: string }> };
      };
      code = payload.error?.details?.find((detail) =>
        detail.code === 'demo_listing_limit_reached'
      )?.code;
    } catch {
      // An unstructured error body must not replace the safe status message.
    }
    throw new ListingsApiError(response.status, code);
  }
  if (response.status === 204) return undefined as T;
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

/** Change owner availability through the revision-guarded Listings operation. */
export const changeListingAvailability = (
  listingId: string,
  body: AvailabilityChange,
) => listingsRequest<ListingDetail>(
  `/listings/${encodeURIComponent(listingId)}/availability`,
  { method: 'PUT', body: JSON.stringify(body) },
);

/** Change the selected buyer through Listings' owner- and revision-checked command. */
export const setSelectedListingBuyer = (
  listingId: string,
  body: SelectionChange,
) => listingsRequest<ListingOwnerView>(
  `/listings/${encodeURIComponent(listingId)}/selection`,
  { method: 'PUT', body: JSON.stringify(body) },
);

export const createImageUpload = (body: ImageUploadRequest, signal?: AbortSignal) =>
  listingsRequest<UploadInstruction>('/image-uploads', {
    method: 'POST', body: JSON.stringify(body), signal,
  });

export const confirmImageUpload = (uploadId: string, signal?: AbortSignal) =>
  listingsRequest<ConfirmedImage>(
    `/image-uploads/${encodeURIComponent(uploadId)}/confirm`,
    { method: 'POST', signal },
  );

export const cancelImageUpload = (uploadId: string) =>
  listingsRequest<void>(
    `/image-uploads/${encodeURIComponent(uploadId)}`,
    { method: 'DELETE' },
  );

const imageDeliveryBatch = batchedRead<ImageDelivery | null>(async (ids, signal) => {
  const query = new URLSearchParams();
  for (const id of ids) query.append('image_ids', id);
  const value = await listingsRequest<ImageDeliveryBatch>(`/images/delivery?${query}`, { signal });
  if (!value || !Array.isArray(value.items) || value.items.length !== ids.length) throw new ListingsApiError(503);
  const result = new Map<string, ImageDelivery | null>();
  for (const item of value.items) {
    if (!item || !ids.includes(item.image_id) || result.has(item.image_id)) throw new ListingsApiError(503);
    if (item.delivery !== null) {
      const delivery = item.delivery;
      if (!delivery || typeof delivery.url !== 'string' || typeof delivery.url_expires_at !== 'string') throw new ListingsApiError(503);
      const url = new URL(delivery.url);
      const expires = Date.parse(delivery.url_expires_at);
      if (url.protocol !== 'https:' || url.username || url.password || !Number.isFinite(expires) ||
          expires <= Date.now() || expires > Date.now() + 301_000) throw new ListingsApiError(503);
    }
    result.set(item.image_id, item.delivery);
  }
  return result;
});

/** Resolve current page links in one request; no signed URL cache survives a view. */
export async function readImageDelivery(imageId: string, signal?: AbortSignal): Promise<ImageDelivery> {
  const delivery = await imageDeliveryBatch(imageId, signal);
  if (!delivery) throw new ListingsApiError(404);
  return delivery;
}

function putImageBytes(
  file: File,
  instruction: UploadInstruction,
  onProgress: (percentage: number) => void,
  signal?: AbortSignal,
): Promise<number> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    if (signal?.aborted) {
      reject(new DOMException('Upload cancelled', 'AbortError'));
      return;
    }
    const abort = () => request.abort();
    request.open('PUT', instruction.upload_url);
    for (const [name, value] of Object.entries(instruction.required_headers)) {
      request.setRequestHeader(name, value);
    }
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.min(99, Math.round((event.loaded / event.total) * 100)));
      }
    };
    request.onload = () => resolve(request.status);
    request.onerror = () => reject(new Error('The photo could not be sent. Check your connection and retry.'));
    request.ontimeout = () => reject(new Error('The photo upload took too long. Retry the photo.'));
    request.onabort = () => reject(new DOMException('Upload cancelled', 'AbortError'));
    request.onloadend = () => signal?.removeEventListener('abort', abort);
    signal?.addEventListener('abort', abort, { once: true });
    request.timeout = 120_000;
    request.send(file);
  });
}

/** Preserve recoverable errors while explaining uploads that need a new selection. */
async function confirmUploadedImage(uploadId: string, signal?: AbortSignal) {
  try {
    return await confirmImageUpload(uploadId, signal);
  } catch (error) {
    if (error instanceof ListingsApiError && error.status === 422) {
      throw new ListingImageFinalError('This file could not be verified as a valid JPEG, PNG, or WebP photo of 10 MiB or smaller. Remove it and choose another photo.');
    }
    if (error instanceof ListingsApiError && error.status === 409) {
      throw new ListingImageFinalError('This photo upload expired or is no longer usable. Remove it and choose the photo again.');
    }
    throw error;
  }
}

/** Upload bytes directly to the private object store, then confirm server-inspected content. */
export async function uploadListingImage(
  file: File,
  operationId: string,
  onProgress: (percentage: number) => void,
  onIntent: (uploadId: string) => void,
  previousUploadId?: string,
  signal?: AbortSignal,
): Promise<ConfirmedImage> {
  // A lost confirmation response may hide an already-confirmed object. Check
  // that same ID before asking for another upload URL or sending bytes again.
  if (previousUploadId) {
    try {
      const confirmed = await confirmUploadedImage(previousUploadId, signal);
      onProgress(100);
      return confirmed;
    } catch (error) {
      if (!(error instanceof ListingsApiError && error.status === 404)) throw error;
      // The object is absent; replay the original intent and send the same file.
    }
  }
  const requestBody: ImageUploadRequest = {
    media_type: file.type as ImageUploadRequest['media_type'],
    size_bytes: file.size,
    operation_id: operationId,
  };
  let instruction: UploadInstruction;
  try {
    instruction = await createImageUpload(requestBody, signal);
  } catch (error) {
    if (error instanceof ListingsApiError && error.status === 409) {
      throw new ListingImageFinalError('This photo upload expired. Remove it and choose the photo again.');
    }
    throw error;
  }
  onIntent(instruction.upload_id);
  let status = await putImageBytes(file, instruction, onProgress, signal);

  // A signed URL can expire while the seller is choosing/uploading a large photo.
  // Replaying the same idempotency key mints a fresh URL for the same object key.
  if (status === 403) {
    try {
      instruction = await createImageUpload(requestBody, signal);
    } catch (error) {
      if (error instanceof ListingsApiError && error.status === 409) {
        throw new ListingImageFinalError('This photo upload expired. Remove it and choose the photo again.');
      }
      throw error;
    }
    status = await putImageBytes(file, instruction, onProgress, signal);
  }

  // 412 means a prior attempt may have stored the complete create-only object;
  // the server's confirmation step inspects it before accepting the image.
  if ((status < 200 || status >= 300) && status !== 412) {
    throw new Error(status === 403
      ? 'The photo upload link expired or was rejected. Retry the photo.'
      : 'The photo could not be uploaded. Retry the photo.');
  }
  onProgress(100);
  return confirmUploadedImage(instruction.upload_id, signal);
}

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

/** Submit/revise through Listings so availability and participant checks serialize with writes. */
export const submitListingOffer = (listingId: string, conversationId: string, body: OfferRevisionRequest) =>
  listingsRequest<OfferView>(`/listings/${encodeURIComponent(listingId)}/conversations/${encodeURIComponent(conversationId)}/offer`,
    { method: 'PUT', body: JSON.stringify(body) });

/** Withdraw through the same owner boundary, including the current offer revision. */
export const withdrawListingOffer = (listingId: string, conversationId: string, body: OfferWithdrawalRequest) =>
  listingsRequest<OfferView>(`/listings/${encodeURIComponent(listingId)}/conversations/${encodeURIComponent(conversationId)}/offer-withdrawals`,
    { method: 'POST', body: JSON.stringify(body) });
