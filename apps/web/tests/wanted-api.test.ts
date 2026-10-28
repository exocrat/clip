import { withCsrf } from './helpers/csrf';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  browseWanted,
  budgetPaise,
  changeWantedState,
  contactRequester,
  createWanted,
  draftMatches,
  editWanted,
  ownWanted,
  readSaved,
  readSearchSession,
  readWanted,
  saveListing,
  SearchIntent,
  unsaveListing,
} from '../src/features/search/wantedApi';
import { parseWantedDiscoveryQuery } from '../src/features/search/wantedDiscoveryQuery';
const id = '20000000-0000-4000-8000-000000000001';
const operation_id = '20000000-0000-4000-8000-000000000002';
const time = '2026-01-01T00:00:00.000000Z';
const wanted = {
  request_id: id,
  title: 'A bicycle',
  description: 'For campus trips',
  category_code: 'bicycles',
  category_label: 'Bicycles',
  budget_paise: null,
  created_at: time,
  updated_at: time,
};
const owner = { ...wanted, state: 'open', revision: 1 };
const listing = {
  listing_id: id,
  title: 'Campus bicycle',
  description: 'Synthetic fixture',
  category_code: 'bicycles',
  category_label: 'Bicycles',
  condition_code: 'good',
  condition_label: 'Good',
  asking_price_paise: 0,
  original_price_paise: null,
  negotiable: false,
  pickup_area: null,
  available_from: time,
  available_until: null,
  availability: 'unavailable',
  sensitive_purchase: false,
  image_ids: [],
};
const page = (items: unknown[]) => ({ items, page: 1, page_size: 20, has_next: false });
const signal = () => new AbortController().signal;
function stub(value: unknown, status = 200) {
  const fetch = vi
    .fn()
    .mockResolvedValue(new Response(status === 204 ? null : JSON.stringify(value), { status }));
  vi.stubGlobal('fetch', withCsrf(fetch));
  return fetch;
}
afterEach(() => vi.unstubAllGlobals());

describe('wanted forms and private API transport', () => {
  it('reads reviewed public and private pages without caller-selected identity or caching', async () => {
    const fetch = stub(page([wanted]));
    await browseWanted(1, signal());
    expect(fetch).toHaveBeenCalledWith(
      '/api/wanted-requests?page=1&page_size=20',
      expect.objectContaining({ method: 'GET', credentials: 'same-origin', cache: 'no-store' }),
    );
    const privateFetch = stub(page([owner]));
    await ownWanted(1, signal());
    expect(privateFetch.mock.calls[0][0]).toBe('/api/me/wanted-requests?page=1&page_size=20');
  });
  it('sends repeated category and exact whole-rupee budget discovery filters', async () => {
    const query = parseWantedDiscoveryQuery(new URLSearchParams(
      'q=physics&category_code=books&category_code=bicycles&min_budget_paise=0&max_budget_paise=250000&page=2&page_size=50',
    ));
    const fetch = stub({ items: [], page: 2, page_size: 50, has_next: false });
    await browseWanted(query, signal());
    expect(fetch.mock.calls[0][0]).toBe(
      '/api/wanted-requests?q=physics&category_code=bicycles&category_code=books&min_budget_paise=0&max_budget_paise=250000&page=2&page_size=50',
    );
  });
  it('keeps unavailable owner detail, but refuses private fields on public browse', async () => {
    stub({ ...owner, state: 'unavailable' });
    await expect(readWanted(id, signal())).resolves.toMatchObject({ state: 'unavailable' });
    stub(page([owner]));
    await expect(browseWanted(1, signal())).rejects.toMatchObject({ status: 0 });
    stub(page([{ ...wanted, author_id: id }]));
    await expect(browseWanted(1, signal())).rejects.toMatchObject({ status: 0 });
  });
  it.each(['duplicate', 'wrong-page', 'lookahead', 'unsafe-budget', 'missing-title', 'invalid-budget'])(
    'rejects malformed wanted data: %s',
    async (kind) => {
      let item: Record<string, unknown> = { ...wanted };
      if (kind === 'unsafe-budget') item.budget_paise = Number.MAX_SAFE_INTEGER + 1;
      if (kind === 'missing-title') {
        const { title: _title, ...rest } = item;
        item = rest;
      }
      if (kind === 'invalid-budget') item.budget_paise = '0';
      stub({
        ...page(kind === 'duplicate' ? [item, item] : [item]),
        ...(kind === 'wrong-page' ? { page: 2 } : {}),
        ...(kind === 'lookahead' ? { has_next: true } : {}),
      });
      await expect(browseWanted(1, signal())).rejects.toMatchObject({ status: 0 });
    },
  );
  it('sends exact create/edit/state shapes and preserves explicit null and free budgets', async () => {
    const fields = {
      title: wanted.title,
      description: wanted.description,
      category_code: wanted.category_code,
      budget_paise: null,
      operation_id,
    };
    const fetch = stub(owner, 201);
    await createWanted(fields, signal());
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual(fields);
    const patch = { operation_id, expected_revision: 1, budget_paise: 0 };
    const edit = stub(owner);
    await editWanted(id, patch, signal());
    expect(JSON.parse(edit.mock.calls[0][1].body)).toEqual(patch);
    const state = { operation_id, expected_revision: 1, state: 'unavailable' as const };
    const change = stub({ ...owner, state: 'unavailable' });
    await changeWantedState(id, state, signal());
    expect(change.mock.calls[0][0]).toBe(`/api/wanted-requests/${id}/availability`);
    expect(JSON.parse(change.mock.calls[0][1].body)).toEqual(state);
  });
  it('draft matches send title only; unavailable results and diagnostic extras are rejected', async () => {
    const fetch = stub({ items: [], has_more: false });
    await draftMatches('bicycle', signal());
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ draft_title: 'bicycle' });
    stub({ items: [listing], has_more: false });
    await expect(draftMatches('bicycle', signal())).rejects.toMatchObject({ status: 0 });
  });
  it.each([401, 403, 404, 409, 422, 503])(
    'preserves safe status %s with no automatic write retry',
    async (status) => {
      const fetch = stub({ private_detail: 'DO-NOT-REFLECT' }, status);
      await expect(
        createWanted({ title: 'A', description: 'B', category_code: 'books', operation_id }, signal()),
      ).rejects.toMatchObject({ status });
      expect(fetch).toHaveBeenCalledTimes(1);
      await expect(
        createWanted({ title: 'A', description: 'B', category_code: 'books', operation_id }, signal()),
      ).rejects.not.toThrow('DO-NOT-REFLECT');
    },
  );
  it('does not convert aborts into user-facing failures', async () => {
    const controller = new AbortController();
    controller.abort();
    const error = new DOMException('abort', 'AbortError');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error));
    await expect(browseWanted(1, controller.signal)).rejects.toMatchObject({ name: 'AbortError' });
  });
});

describe('regular-only response and backend confirmation', () => {
  it.each(['regular', 'temporary'])('reads the actual %s session contract', async (account_class) => {
    const fetch = stub({
      user_id: id,
      account_class,
      valid_until: '2099-01-01T00:00:00.000000Z',
      display_name: null,
    });
    await expect(readSearchSession(signal())).resolves.toMatchObject({ account_class });
    expect(fetch.mock.calls[0][0]).toBe('/api/me');
  });
  it('rejects expired or missing session eligibility', async () => {
    stub({ user_id: id, account_class: 'regular', valid_until: time });
    await expect(readSearchSession(signal())).rejects.toMatchObject({ status: 0 });
    stub({ user_id: id });
    await expect(readSearchSession(signal())).rejects.toMatchObject({ status: 0 });
  });
  it.each([200, 201])('accepts the reviewed %s conversation body, never a fabricated ID', async (status) => {
    const fetch = stub({ conversation_id: id, created: status === 201 }, status);
    await expect(contactRequester(id, operation_id, signal())).resolves.toMatchObject({
      conversation_id: id,
    });
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ operation_id });
    stub({}, status);
    await expect(contactRequester(id, operation_id, signal())).rejects.toMatchObject({ status: 0 });
  });
});

describe('private saved current state and retirement', () => {
  it('preserves unavailable detail and accepts only content-free retired references', async () => {
    stub(page([{ listing_id: id, saved_at: time, retired: false, listing }]));
    await expect(readSaved(1, signal())).resolves.toMatchObject({
      items: [{ listing: { availability: 'unavailable' } }],
    });
    stub(page([{ listing_id: id, saved_at: time, retired: true, listing: null }]));
    await expect(readSaved(1, signal())).resolves.toMatchObject({ items: [{ listing: null }] });
    stub(page([{ listing_id: id, saved_at: time, retired: true, listing }]));
    await expect(readSaved(1, signal())).rejects.toMatchObject({ status: 0 });
  });
  it('rejects mismatched saved IDs and private listing fields', async () => {
    for (const wrong of [
      { ...listing, listing_id: operation_id },
      { ...listing, owner_id: id },
    ]) {
      stub(page([{ listing_id: id, saved_at: time, retired: false, listing: wrong }]));
      await expect(readSaved(1, signal())).rejects.toMatchObject({ status: 0 });
    }
  });
  it('uses idempotent pair paths for save and empty-204 unsave', async () => {
    const put = stub({ listing_id: id, saved_at: time });
    await saveListing(id, operation_id, signal());
    expect(put.mock.calls[0][0]).toBe(`/api/me/saved-listings/${id}`);
    expect(put.mock.calls[0][1].method).toBe('PUT');
    const remove = stub(null, 204);
    await expect(unsaveListing(id, signal())).resolves.toBeNull();
    expect(remove.mock.calls[0][1].method).toBe('DELETE');
    expect(remove.mock.calls[0][1].body).toBeUndefined();
  });
});

describe('exact budget and unknown-outcome retries', () => {
  it.each([
    ['', null],
    ['  ', null],
    ['0', 0],
    ['125', 12500],
    ['10000000', 1000000000],
  ])('maps %j without rounding', (input, result) => expect(budgetPaise(input)).toBe(result));
  it('rejects amounts above the inclusive ₹1 crore marketplace cap', () =>
    expect(() => budgetPaise('10000001')).toThrow('₹1,00,00,000'),
  );
  it.each(['1.5', '-1', '1e3', 'Infinity', '90071992547410'])('rejects %s', (input) =>
    expect(() => budgetPaise(input)).toThrow(),
  );
  it('retains an identical intent, changes keys for changed writes and resets after confirmation', () => {
    const keys = new SearchIntent();
    const first = keys.key({ budget_paise: null });
    expect(keys.key({ budget_paise: null })).toBe(first);
    expect(keys.key({ budget_paise: 0 })).not.toBe(first);
    keys.clear();
    expect(keys.key({ budget_paise: null })).not.toBe(first);
  });
});
