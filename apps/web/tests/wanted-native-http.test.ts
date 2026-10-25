import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  browseWanted,
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
  unsaveListing,
} from '../src/features/search/wantedApi';
const signal = () => new AbortController().signal;
/** Explicit opt-in only: fixed loopback test harness, never an ambient/hosted target.
 * This exercises the same TS transport used by UI controls against real Search SQL,
 * not React effects, actual Identity/Conversations or browser/device acceptance. */
describe.skipIf(process.env.CLIP_WANTED_UI_HTTP !== 'true')('native Search UI/API boundary', () => {
  afterEach(() => vi.unstubAllGlobals());
  it('round-trips create/edit/null/free/close/reopen, public privacy and draft matching', async () => {
    const realFetch = globalThis.fetch;
    vi.stubGlobal('fetch', (path: string, options: RequestInit) =>
      realFetch(`http://127.0.0.1:8000${path.replace(/^\/api/, '')}`, options),
    );
    await expect(readSearchSession(signal())).resolves.toMatchObject({ account_class: 'regular' });
    const before = await ownWanted(1, signal());
    const created = await createWanted(
      {
        title: 'Bicycle UI boundary check',
        description: 'Synthetic native HTTP verification.',
        category_code: 'bicycles',
        budget_paise: 0,
        operation_id: crypto.randomUUID(),
      },
      signal(),
    );
    expect(created.budget_paise).toBe(0);
    const edited = await editWanted(
      created.request_id,
      { expected_revision: created.revision, budget_paise: null, operation_id: crypto.randomUUID() },
      signal(),
    );
    expect(edited.budget_paise).toBeNull();
    const closed = await changeWantedState(
      created.request_id,
      { expected_revision: edited.revision, state: 'unavailable', operation_id: crypto.randomUUID() },
      signal(),
    );
    expect(closed.state).toBe('unavailable');
    expect(await readWanted(created.request_id, signal())).toMatchObject({ state: 'unavailable' });
    expect(
      (await browseWanted(1, signal())).items.some((item) => item.request_id === created.request_id),
    ).toBe(false);
    const reopened = await changeWantedState(
      created.request_id,
      { expected_revision: closed.revision, state: 'open', operation_id: crypto.randomUUID() },
      signal(),
    );
    expect(reopened.state).toBe('open');
    const page = await browseWanted(1, signal());
    expect(page.items.some((item) => item.request_id === created.request_id)).toBe(true);
    expect(page.items.every((item) => !('revision' in item) && !('author_id' in item))).toBe(true);
    const matches = await draftMatches('bicycle', signal());
    expect(matches.items.length).toBeGreaterThan(0);
    expect((await ownWanted(1, signal())).items.length).toBe(before.items.length + 1);
    await changeWantedState(
      created.request_id,
      { expected_revision: reopened.revision, state: 'unavailable', operation_id: crypto.randomUUID() },
      signal(),
    );
  });
  it('round-trips private save/unsave while retaining unavailable summaries and truthful response failure', async () => {
    const realFetch = globalThis.fetch;
    vi.stubGlobal('fetch', (path: string, options: RequestInit) =>
      realFetch(`http://127.0.0.1:8000${path.replace(/^\/api/, '')}`, options),
    );
    const saved = await readSaved(1, signal());
    expect(saved.items.some((item) => item.listing?.availability === 'unavailable')).toBe(true);
    const current = saved.items.find((item) => item.listing?.availability === 'available');
    expect(current).toBeDefined();
    if (!current) throw new Error('The fixed preview seed is missing.');
    const retry = await saveListing(current.listing_id, crypto.randomUUID(), signal());
    expect(retry.saved_at).toBe(current.saved_at);
    await unsaveListing(current.listing_id, signal());
    expect((await readSaved(1, signal())).items.some((item) => item.listing_id === current.listing_id)).toBe(
      false,
    );
    await saveListing(current.listing_id, crypto.randomUUID(), signal());
    expect((await readSaved(1, signal())).items.some((item) => item.listing_id === current.listing_id)).toBe(
      true,
    );
    const publicRequests = await browseWanted(1, signal());
    await expect(
      contactRequester(publicRequests.items[0].request_id, crypto.randomUUID(), signal()),
    ).rejects.toMatchObject({ status: 503 });
  });
});
