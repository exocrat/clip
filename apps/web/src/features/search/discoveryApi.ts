import type { CatalogueView, ListingSummary, PageResultListingSummary } from '../../../../../contracts/generated/types.gen';
import { MAX_MARKETPLACE_PRICE_PAISE } from '../../shared/money';
import { discoveryParams, type DiscoveryQuery } from './discoveryQuery';

export type { CatalogueView, ListingSummary, PageResultListingSummary };

/** Status-only errors never reflect rejected fields, credentials or provider diagnostics. */
export class DiscoveryApiError extends Error {
  constructor(public readonly status: number) {
    super(({ 401: 'Your session is missing or expired. Sign in to browse listings.',
      403: 'This account is not currently eligible to browse listings.',
      422: 'Some filters were rejected. Check them and apply again.',
      429: 'Too many requests. Wait a moment, then retry.',
      503: 'Listings are temporarily unavailable. Your filters have been kept.' } as Record<number, string>)[status]
      ?? 'Listings could not be loaded safely. Please retry.');
  }
}

let previewBackend: 'unknown' | 'fixtures' | 'native' = 'unknown';

/** Development disclosure only: identify the responding backend, never select auth/routing. */
export function discoveryPreviewBackend(): 'unknown' | 'fixtures' | 'native' {
  return previewBackend;
}

/** Read same-origin, uncached JSON; cancellation is preserved and retries are explicit. */
async function getJson(path: string, signal: AbortSignal): Promise<unknown> {
  try {
    const preview = import.meta.env.DEV && import.meta.env.VITE_SEARCH_UI_PREVIEW === 'true';
    const response = await fetch(`/api${path}`, { signal, credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', ...(preview ? { 'X-Clip-UI-Preview': 'search-fixtures' } : {}) } });
    if (preview) {
      const kind = response.headers.get('X-Clip-Preview');
      previewBackend = kind === 'search-native-model-synthetic-identity' ? 'native'
        : kind === 'search-ui-fixtures' ? 'fixtures' : 'unknown';
    }
    if (!response.ok) throw new DiscoveryApiError(response.status);
    return await response.json();
  } catch (error) {
    if (signal.aborted || (error instanceof DOMException && error.name === 'AbortError')) throw error;
    if (error instanceof DiscoveryApiError) throw error;
    throw new DiscoveryApiError(0);
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function keys(value: Record<string, unknown>, expected: string[]): boolean {
  return Object.keys(value).length === expected.length && expected.every((key) => Object.hasOwn(value, key));
}

const uuid = (value: unknown): value is string => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(value);
const instant = (value: unknown): value is string => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$/.test(value) && Number.isFinite(Date.parse(value));

/** Check every reviewed public field before exposing it to the UI; no private extras. */
function summary(value: unknown): value is ListingSummary {
  if (!record(value) || !keys(value, ['listing_id', 'title', 'description', 'category_code', 'category_label', 'condition_code', 'condition_label', 'asking_price_paise', 'original_price_paise', 'negotiable', 'pickup_area', 'available_from', 'available_until', 'availability', 'sensitive_purchase', 'image_ids'])) return false;
  return uuid(value.listing_id) && typeof value.title === 'string' && value.title.trim().length > 0 && [...value.title].length <= 120
    && typeof value.description === 'string' && [...value.description].length <= 5000
    && ['category_code', 'category_label', 'condition_code', 'condition_label'].every((key) => typeof value[key] === 'string' && value[key] !== '')
    && typeof value.asking_price_paise === 'number' && Number.isSafeInteger(value.asking_price_paise) && value.asking_price_paise >= 0 && value.asking_price_paise <= MAX_MARKETPLACE_PRICE_PAISE && value.asking_price_paise % 100 === 0
    && (value.original_price_paise === null || (typeof value.original_price_paise === 'number' && Number.isSafeInteger(value.original_price_paise) && value.original_price_paise > 0 && value.original_price_paise <= MAX_MARKETPLACE_PRICE_PAISE && value.original_price_paise % 100 === 0))
    && typeof value.negotiable === 'boolean' && (value.pickup_area === null || typeof value.pickup_area === 'string')
    && instant(value.available_from) && (value.available_until === null || instant(value.available_until))
    && value.availability === 'available' && typeof value.sensitive_purchase === 'boolean'
    && Array.isArray(value.image_ids) && value.image_ids.every(uuid);
}

/** Validate the catalogue shape; options remain owned by Listings, never a copied enum. */
export async function readDiscoveryCatalogue(signal: AbortSignal): Promise<CatalogueView> {
  const value = await getJson('/catalogue', signal);
  const entries = (items: unknown): boolean => Array.isArray(items) && items.every((item) => record(item) && keys(item, ['code', 'label']) && typeof item.code === 'string' && item.code !== '' && typeof item.label === 'string' && item.label !== '')
    && new Set(items.map((item) => item.code)).size === items.length;
  if (!record(value) || !keys(value, ['categories', 'conditions']) || !entries(value.categories) || !entries(value.conditions)) throw new DiscoveryApiError(0);
  return value as CatalogueView;
}

/** Validate page coordinates, public summaries and lookahead semantics against the query. */
export async function readDiscoveryPage(query: DiscoveryQuery, signal: AbortSignal): Promise<PageResultListingSummary> {
  const params = discoveryParams(query);
  // The API default remains newest-first; send automatic match ordering for
  // nonblank website searches when the bookmark leaves sort implicit.
  if (query.q && query.sort === 'relevance' && !params.has('sort')) params.set('sort', 'relevance');
  // UI defaults differ from the public API default: always send the chosen mode.
  params.set('search_mode', query.search_mode);
  const suffix = params.toString();
  const value = await getJson(`/listings${suffix ? `?${suffix}` : ''}`, signal);
  if (!record(value) || !keys(value, ['items', 'page', 'page_size', 'has_next']) || value.page !== query.page || value.page_size !== query.page_size
    || typeof value.has_next !== 'boolean' || !Array.isArray(value.items) || value.items.length > query.page_size || !value.items.every(summary)
    || (value.has_next && value.items.length !== query.page_size)
    || new Set(value.items.map((item) => item.listing_id)).size !== value.items.length) throw new DiscoveryApiError(0);
  return value as PageResultListingSummary;
}

/** Format only previously validated integer paise; never round server money. */
export function discoveryPrice(paise: number): string {
  return `₹${new Intl.NumberFormat('en-IN').format(BigInt(paise) / 100n)}`;
}
