import { sessionFetch, SessionFetchError } from '../../shared/http/sessionFetch';
import { batchedRead } from '../../shared/http/batchedRead';
import type {
  ConversationStartResult,
  CreateWantedRequest,
  DraftMatchResult,
  PageResultSavedListingView,
  PageResultWantedRequestOwnerView,
  PageResultWantedRequestPublic,
  SavedListingAck,
  SavedStatusBatch,
  SessionView,
  WantedRequestOwnerView,
  WantedRequestPatch,
  WantedRequestPublic,
  WantedRequestStateChange,
} from '../../../../../contracts/generated/types.gen';
import { wantedDiscoveryParams, type WantedDiscoveryQuery } from './wantedDiscoveryQuery';
import { MAX_MARKETPLACE_PRICE_PAISE, MAX_MARKETPLACE_RUPEES } from '../../shared/money';
export type { WantedRequestOwnerView, WantedRequestPublic };

/** Fixed messages keep rejected input and provider diagnostics out of the UI. */
export class WantedApiError extends Error {
  constructor(public readonly status: number) {
    super(
      (
        {
          401: 'Your session has expired. Sign in again.',
          403: 'This action is not available to this account.',
          404: 'This item is no longer available to you.',
          409: 'This request changed. Reload it before editing again.',
          413: 'This request is too large. Reduce its contents and try again.',
          422: 'Use a title up to 120 characters, description up to 5,000, a current category, and an optional whole-rupee budget up to ₹1,00,00,000.',
          503: 'This service is temporarily unavailable. Please retry.',
        } as Record<number, string>
      )[status] ?? 'The request could not be confirmed. Please retry.',
    );
  }
}
/** Runtime shape primitives reject malformed IDs, instants and unsafe integer money. */
const object = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v);
export const validSearchId = (v: unknown): v is string =>
  typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v);
const instant = (v: unknown) =>
  typeof v === 'string' &&
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$/.test(v) &&
  Number.isFinite(Date.parse(v));
const exact = (v: Record<string, unknown>, fields: string[]) =>
  Object.keys(v).length === fields.length && fields.every((k) => Object.hasOwn(v, k));
const money = (v: unknown) =>
  v === null || (typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 && v <= MAX_MARKETPLACE_PRICE_PAISE && v % 100 === 0);
const text = (v: unknown, max: number) =>
  typeof v === 'string' && v.trim().length > 0 && [...v].length <= max;

/** Validate the public projection before rendering. Owner metadata is accepted only on private reads. */
export function isWanted(v: unknown, owner = false): boolean {
  if (!object(v)) return false;
  const fields = [
    'request_id',
    'title',
    'description',
    'category_code',
    'category_label',
    'budget_paise',
    'created_at',
    'updated_at',
    ...(owner ? ['state', 'revision'] : []),
  ];
  return (
    Object.keys(v).every((k) => fields.includes(k)) &&
    fields.filter((k) => k !== 'budget_paise').every((k) => Object.hasOwn(v, k)) &&
    validSearchId(v.request_id) &&
    text(v.title, 120) &&
    text(v.description, 5000) &&
    text(v.category_code, 100) &&
    text(v.category_label, 200) &&
    money(v.budget_paise === undefined ? null : v.budget_paise) &&
    instant(v.created_at) &&
    instant(v.updated_at) &&
    (!owner ||
      (['open', 'unavailable'].includes(String(v.state)) &&
        Number.isSafeInteger(v.revision) &&
        Number(v.revision) >= 1))
  );
}

let isolatedPreview = false;
/** Disclosure from the responding test server, never an authentication or routing selector. */
export const wantedPreviewActive = () => isolatedPreview;

/** Shared uncached transport. Writes never retry automatically or store private data persistently. */
async function request<T>(
  path: string,
  signal: AbortSignal,
  validate: (v: unknown) => boolean,
  method = 'GET',
  body?: unknown,
): Promise<T> {
  try {
    const response = await sessionFetch(path, {
      method,
      signal,
      credentials: 'same-origin',
      cache: 'no-store',
      headers: {
        Accept: 'application/json',
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    isolatedPreview =
      import.meta.env.DEV &&
      response.headers.get('X-Clip-Preview') === 'search-wanted-native-synthetic-identity';
    if (!response.ok) throw new WantedApiError(response.status);
    const value: unknown = response.status === 204 ? null : await response.json();
    if (!validate(value)) throw new WantedApiError(0);
    return value as T;
  } catch (error) {
    if (signal.aborted || error instanceof WantedApiError) throw error;
    throw new WantedApiError(error instanceof SessionFetchError ? error.status : 0);
  }
}
/** Refuse wrong-page, duplicate and impossible lookahead data rather than mixing private pages. */
const page = (
  number: number,
  item: (v: unknown) => boolean,
  idField: string,
  pageSize = 20,
) => (v: unknown) =>
  object(v) &&
  exact(v, ['items', 'has_next', 'page', 'page_size']) &&
  Array.isArray(v.items) &&
  v.items.every(item) &&
  typeof v.has_next === 'boolean' &&
  v.page === number &&
  v.page_size === pageSize &&
  v.items.length <= pageSize &&
  (!v.has_next || v.items.length === pageSize) &&
  new Set(v.items.map((entry) => (object(entry) ? entry[idField] : null))).size === v.items.length;
export const readWanted = (id: string, signal: AbortSignal) =>
  request<WantedRequestPublic | WantedRequestOwnerView>(
    `/wanted-requests/${id}`,
    signal,
    (v) => isWanted(v) || isWanted(v, true),
  );
/** Read a public wanted page using API filter names; numbers preserve legacy paging calls. */
export const browseWanted = (query: WantedDiscoveryQuery | number, signal: AbortSignal) => {
  const values = typeof query === 'number'
    ? { page: query, page_size: 20 as const }
    : query;
  const params = typeof query === 'number'
    ? new URLSearchParams({ page: String(query), page_size: '20' })
    : wantedDiscoveryParams(query);
  const suffix = params.toString();
  return request<PageResultWantedRequestPublic>(
    `/wanted-requests${suffix ? `?${suffix}` : ''}`,
    signal,
    page(values.page, (v) => isWanted(v), 'request_id', values.page_size),
  );
};
export const ownWanted = (number: number, signal: AbortSignal) =>
  request<PageResultWantedRequestOwnerView>(
    `/me/wanted-requests?page=${number}&page_size=20`,
    signal,
    page(number, (v) => isWanted(v, true), 'request_id'),
  );
export const createWanted = (body: CreateWantedRequest, signal: AbortSignal) =>
  request<WantedRequestOwnerView>('/wanted-requests', signal, (v) => isWanted(v, true), 'POST', body);
export const editWanted = (id: string, body: WantedRequestPatch, signal: AbortSignal) =>
  request<WantedRequestOwnerView>(`/wanted-requests/${id}`, signal, (v) => isWanted(v, true), 'PATCH', body);
export const changeWantedState = (id: string, body: WantedRequestStateChange, signal: AbortSignal) =>
  request<WantedRequestOwnerView>(
    `/wanted-requests/${id}/availability`,
    signal,
    (v) => isWanted(v, true),
    'PUT',
    body,
  );

/** Read the existing public session contract, never infer regular membership from a successful browse. */
export const readSearchSession = (signal: AbortSignal) =>
  request<SessionView>(
    '/me',
    signal,
    (v) =>
      object(v) &&
      validSearchId(v.user_id) &&
      ['regular', 'temporary'].includes(String(v.account_class)) &&
      instant(v.valid_until) &&
      Date.parse(String(v.valid_until)) > Date.now(),
  );
export const contactRequester = (id: string, operationId: string, signal: AbortSignal) =>
  request<ConversationStartResult>(
    `/wanted-requests/${id}/conversations`,
    signal,
    (v) =>
      object(v) &&
      Object.keys(v).length === 2 &&
      validSearchId(v.conversation_id) &&
      typeof v.created === 'boolean',
    'POST',
    { operation_id: operationId },
  );

/** Listing projection validation permits unavailable saved items; retired items must contain no content. */
export function isSearchListing(v: unknown): boolean {
  return (
    object(v) &&
    exact(v, [
      'listing_id',
      'title',
      'description',
      'category_code',
      'category_label',
      'condition_code',
      'condition_label',
      'asking_price_paise',
      'original_price_paise',
      'negotiable',
      'pickup_area',
      'available_from',
      'available_until',
      'availability',
      'sensitive_purchase',
      'image_ids',
    ]) &&
    validSearchId(v.listing_id) &&
    text(v.title, 120) &&
    typeof v.description === 'string' &&
    [...v.description].length <= 5000 &&
    ['category_code', 'category_label', 'condition_code', 'condition_label'].every(
      (k) => typeof v[k] === 'string' && v[k] !== '',
    ) &&
    money(v.asking_price_paise) &&
    v.asking_price_paise !== null &&
    (v.original_price_paise === null || (typeof v.original_price_paise === 'number'
      && Number.isSafeInteger(v.original_price_paise) && v.original_price_paise > 0
      && v.original_price_paise <= MAX_MARKETPLACE_PRICE_PAISE && v.original_price_paise % 100 === 0)) &&
    typeof v.negotiable === 'boolean' &&
    typeof v.sensitive_purchase === 'boolean' &&
    (v.pickup_area === null || typeof v.pickup_area === 'string') &&
    Array.isArray(v.image_ids) &&
    v.image_ids.every(validSearchId) &&
    ['available', 'unavailable'].includes(String(v.availability)) &&
    instant(v.available_from) &&
    (v.available_until === null || instant(v.available_until))
  );
}
export const draftMatches = (title: string, signal: AbortSignal) =>
  request<DraftMatchResult>(
    '/wanted-requests/draft-matches',
    signal,
    (v) =>
      object(v) &&
      exact(v, ['items', 'has_more']) &&
      typeof v.has_more === 'boolean' &&
      Array.isArray(v.items) &&
      v.items.length <= 20 &&
      (!v.has_more || v.items.length === 20) &&
      new Set(v.items.map((item) => (object(item) ? item.listing_id : null))).size === v.items.length &&
      v.items.every((item) => isSearchListing(item) && object(item) && item.availability === 'available'),
    'POST',
    { draft_title: title },
  );
const readSavedPage = (number: number, pageSize: 20 | 100, signal: AbortSignal) =>
  request<PageResultSavedListingView>(
    `/me/saved-listings?page=${number}&page_size=${pageSize}`,
    signal,
    page(
      number,
      (v) =>
        object(v) &&
        exact(v, ['listing_id', 'saved_at', 'listing', 'retired']) &&
        validSearchId(v.listing_id) &&
        instant(v.saved_at) &&
        typeof v.retired === 'boolean' &&
        (v.retired
          ? v.listing === null
          : isSearchListing(v.listing) && object(v.listing) && v.listing.listing_id === v.listing_id),
      'listing_id',
      pageSize,
    ),
  );
export const readSaved = (number: number, signal: AbortSignal) =>
  readSavedPage(number, 20, signal);

/** Fetch exactly the current render's IDs once, without traversing saved content. */
export const isListingSaved = batchedRead<boolean>(async (ids, signal) => {
  const query = new URLSearchParams();
  for (const id of ids) query.append('listing_ids', id);
  const value = await request<SavedStatusBatch>(`/me/saved-listings/status?${query}`, signal, (v) =>
    object(v) && exact(v, ['items']) && Array.isArray(v.items) && v.items.length === ids.length &&
    new Set(v.items.map((item) => object(item) ? item.listing_id : null)).size === ids.length &&
    v.items.every((item) => object(item) && exact(item, ['listing_id', 'saved']) &&
      validSearchId(item.listing_id) && ids.includes(item.listing_id) && typeof item.saved === 'boolean'),
  );
  return new Map(value.items.map((item) => [item.listing_id, item.saved]));
});
export const saveListing = (id: string, operationId: string, signal: AbortSignal) =>
  request<SavedListingAck>(
    `/me/saved-listings/${id}`,
    signal,
    (v) => object(v) && v.listing_id === id && instant(v.saved_at),
    'PUT',
    { operation_id: operationId },
  );
export const unsaveListing = (id: string, signal: AbortSignal) =>
  request<null>(`/me/saved-listings/${id}`, signal, (v) => v === null, 'DELETE');

/** Parse whole rupees exactly, preserving blank/null versus free/zero without rounding. */
export function budgetPaise(input: string): number | null {
  const value = input.trim();
  if (!value) return null;
  if (value.length > 8 || !/^\d+$/.test(value))
    throw new Error('Enter a budget in whole rupees, or leave it blank.');
  const paise = BigInt(value) * 100n;
  if (paise > BigInt(MAX_MARKETPLACE_PRICE_PAISE)) throw new Error(`Enter a budget up to ₹${MAX_MARKETPLACE_RUPEES.toLocaleString('en-IN')}, or leave it blank.`);
  return Number(paise);
}

/** Retain an operation key for identical ambiguous retries; changed intent gets a new key. */
export class SearchIntent {
  private previous = '';
  private id = '';
  key(value: unknown): string {
    const next = JSON.stringify(value);
    if (next !== this.previous || !this.id) {
      this.previous = next;
      this.id = crypto.randomUUID();
    }
    return this.id;
  }
  clear() {
    this.previous = '';
    this.id = '';
  }
}
