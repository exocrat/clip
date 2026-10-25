import { readFileSync } from 'node:fs';
import { describe, expect, it, vi } from 'vitest';
import type { ListingSummary, ListingsQueryAvailableData, ListingsQueryAvailableResponses } from '../../../contracts/generated/types.gen';
import { readDiscoveryPage } from '../src/features/search/discoveryApi';
import { DEFAULT_QUERY, discoveryParams } from '../src/features/search/discoveryQuery';

type Schema = { $ref?: string; properties?: Record<string, Schema>; items?: Schema; additionalProperties?: boolean };
type Operation = { operationId: string; parameters: { name: string }[]; responses: Record<string, { content: { 'application/json': { schema: Schema } } }> };
const document = JSON.parse(readFileSync(new URL('../../../contracts/generated/openapi.json', import.meta.url), 'utf8')) as {
  paths: Record<string, { get: Operation }>; components: { schemas: Record<string, Schema> };
};

/** Resolve trusted local OpenAPI schema names without external reference loading. */
function resolve(schema: Schema): Schema {
  if (!schema.$ref?.startsWith('#/components/schemas/')) throw new Error('Expected registered local schema');
  const result = document.components.schemas[schema.$ref.slice('#/components/schemas/'.length)];
  if (!result) throw new Error('Missing registered response schema');
  return result;
}

const summary = { listing_id: '20000000-0000-4000-8000-000000000001', title: 'Synthetic contract bicycle', description: 'Controlled public summary',
  category_code: 'bicycles', category_label: 'Bicycles', condition_code: 'good', condition_label: 'Good', asking_price_paise: 0,
  negotiable: false, pickup_area: null, available_from: '2026-01-01T00:00:00.000000Z', available_until: null,
  availability: 'available', sensitive_purchase: false, image_ids: [] } satisfies ListingSummary;
const page = { items: [summary], page: 1, page_size: 20, has_next: false } satisfies ListingsQueryAvailableResponses[200];

describe('reviewed discovery HTTP operation and generated TypeScript parity', () => {
  it('uses the declared operation and exact public response properties', () => {
    const operation = document.paths['/listings'].get;
    expect(operation.operationId).toBe('listings_query_available');
    const response = resolve(operation.responses['200'].content['application/json'].schema);
    const itemSchema = response.properties?.items.items;
    if (!itemSchema) throw new Error('Missing listing response items');
    const item = resolve(itemSchema);
    expect(Object.keys(page).sort()).toEqual(Object.keys(response.properties ?? {}).sort());
    expect(Object.keys(summary).sort()).toEqual(Object.keys(item.properties ?? {}).sort());
    expect(response.additionalProperties).toBe(false);
    expect(item.additionalProperties).toBe(false);
  });
  it('serializes the registered query vocabulary while preserving zero and false', () => {
    const typed: NonNullable<ListingsQueryAvailableData['query']> = {
      q: 'bicycle', category_code: 'bicycles', condition_code: 'good', min_price_paise: 0,
      max_price_paise: 100, negotiable: false, search_mode: 'hybrid', sort: 'price_desc', page: 2, page_size: 50,
    };
    const params = discoveryParams({ ...DEFAULT_QUERY, ...typed, q: 'bicycle', category_code: 'bicycles', condition_code: 'good',
      min_price_paise: '0', max_price_paise: '100', negotiable: 'false', search_mode: 'hybrid', sort: 'price_desc', page: 2, page_size: 50 });
    expect([...params.keys()].sort()).toEqual(document.paths['/listings'].get.parameters.map((entry) => entry.name).sort());
    expect(document.paths['/listings'].get.parameters.some((entry) => entry.name === 'search_mode')).toBe(true);
    expect(params.get('search_mode')).toBe('hybrid');
    expect(params.get('min_price_paise')).toBe('0');
    expect(params.get('negotiable')).toBe('false');
  });
  it('accepts the reviewed wire shape through the handwritten reader with generated response typing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(page))));
    try {
      const result: ListingsQueryAvailableResponses[200] = await readDiscoveryPage(DEFAULT_QUERY, new AbortController().signal);
      expect(result).toEqual(page);
    } finally { vi.unstubAllGlobals(); }
  });
});
