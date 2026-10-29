import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router';
import { Button, MultiChoiceDropdown } from '../../shared/ui';
import { type DiscoveryApiError, discoveryPreviewBackend,
  type CatalogueView, type PageResultListingSummary } from './discoveryApi';
import { applyDiscoveryForm, DEFAULT_QUERY, discoveryForm, discoveryParams, editDiscoveryText,
  parseDiscoveryQuery, type DiscoveryForm, type DiscoveryQuery } from './discoveryQuery';
import { startDiscoveryRequest } from './discoveryRequest';
import { SaleListingCard } from './SaleListingCard';
import './discovery.css';

type ResultState = { kind: 'loading' } | { kind: 'ready'; page: PageResultListingSummary }
  | { kind: 'error'; error: DiscoveryApiError } | { kind: 'invalid'; message: string };

/** Preserve the inactive Wanted tab's URL filters without passing them to sale search. */
function withWantedRouteState(sale: URLSearchParams, current: URLSearchParams): URLSearchParams {
  const combined = new URLSearchParams(sale);
  current.forEach((value, key) => {
    if (key.startsWith('wanted_')) combined.append(key, value);
  });
  return combined;
}

/** Own discovery state inside Search; other domains supply only reviewed public data. */
export function SaleDiscovery({
  createListingAction,
  renderListingActions,
}: {
  createListingAction?: ReactNode;
  renderListingActions?: (listingId: string) => ReactNode;
}) {
  const [params, setParams] = useSearchParams();
  const key = params.toString();
  const parsed = useMemo(() => {
    try {
      const saleParams = new URLSearchParams(key);
      for (const name of [...saleParams.keys()]) if (name.startsWith('wanted_')) saleParams.delete(name);
      return { query: parseDiscoveryQuery(saleParams) };
    }
    catch (error) { return { message: error instanceof Error ? error.message : 'Check the filters in this URL.' }; }
  }, [key]);
  const query = parsed.query ?? DEFAULT_QUERY;
  const [draft, setDraft] = useState<DiscoveryForm>(() => discoveryForm(query));
  const [formError, setFormError] = useState('');
  const [catalogue, setCatalogue] = useState<CatalogueView>({ categories: [], conditions: [] });
  const [requestResult, setRequestResult] = useState<{ key: string; reload: number; value: ResultState }>({ key, reload: 0, value: { kind: 'loading' } });
  const [reload, setReload] = useState(0);

  // History and explicit legacy-mode URLs resynchronize the filter draft.
  useEffect(() => {
    setDraft(discoveryForm(parsed.query ?? DEFAULT_QUERY));
    setFormError('');
  }, [parsed, key]);

  useEffect(() => {
    const setResult = (value: ResultState) => setRequestResult({ key, reload, value });
    if (!parsed.query) {
      setResult({ kind: 'invalid', message: parsed.message ?? 'Check your filters.' });
      return;
    }
    setResult({ kind: 'loading' });
    return startDiscoveryRequest(parsed.query,
      (options, page) => { setCatalogue(options); setResult({ kind: 'ready', page }); },
      (error) => setResult({ kind: 'error', error }));
  }, [parsed, reload, key]);

  /** Draft edits do not silently change the applied URL/result set. */
  function change<Key extends keyof DiscoveryForm>(field: Key, value: DiscoveryForm[Key]) {
    setDraft((previous) => {
      if (field === 'sort') return { ...previous, sort: value as DiscoveryForm['sort'], sort_explicit: true };
      if (field === 'q') return editDiscoveryText(previous, String(value));
      return { ...previous, [field]: value };
    });
    setFormError('');
  }

  /** Apply all controls together, validating exact rupees and resetting pagination. */
  function submit(event: FormEvent) {
    event.preventDefault();
    try {
      const next = withWantedRouteState(discoveryParams(applyDiscoveryForm(draft, query.search_mode)), params);
      setFormError('');
      if (next.toString() === key) setReload((value) => value + 1);
      else setParams(next);
    } catch (error) { setFormError(error instanceof Error ? error.message : 'Check your filters.'); }
  }

  /** Page navigation keeps applied filters; resetting clears every filter at once. */
  function navigate(next: DiscoveryQuery) {
    const nextParams = withWantedRouteState(discoveryParams(next), params);
    if (nextParams.toString() === key) setReload((value) => value + 1);
    else setParams(nextParams);
  }

  // Hide a preceding request synchronously, before the next effect is scheduled.
  const result: ResultState = requestResult.key === key && requestResult.reload === reload
    ? requestResult.value : { kind: 'loading' };
  const hybridUnavailable = result.kind === 'error' && result.error.status === 503
    && query.search_mode === 'hybrid' && Boolean(query.q);
  const ready = result.kind === 'ready' ? result.page : undefined;
  return (
    <section className="discovery" aria-label="Browse and search sale listings">
      {import.meta.env.DEV && import.meta.env.VITE_SEARCH_UI_PREVIEW === 'true' && (
        <aside className="discovery-preview" aria-label="Isolated preview disclosure">
          {discoveryPreviewBackend() === 'native' ? <>
            <strong>Real search · local test data</strong> · Native PostgreSQL and the offline semantic model are connected.
            Identity and listing/image data are synthetic. Try “cycle”, “bicyle”, “vehicle”, “wheeled vehicle” or “keep food cold”.
            Detail, save and real sign-in remain pending. This session stops after 30 minutes.
          </> : discoveryPreviewBackend() === 'fixtures' ? <>
            <strong>Isolated UI preview</strong> · Synthetic API fixtures only. No database or real sign-in.
            Try “bicycle”, “empty”, “slow”, “retry”, “hybrid-down”, “unavailable”, “denied” or “expired”. Hybrid and relevance responses are scripted, not model/ranking evidence.
          </> : <><strong>Local preview</strong> · Backend identification pending. No real sign-in or marketplace data is provided.</>}
        </aside>
      )}
      <p className="discovery-intro">Find what you need, right here on campus.</p>
      {createListingAction ? <div className="discovery-page-actions">{createListingAction}</div> : null}
      <details open className="search-controls"><summary>Search &amp; filters — {query.q || "All items"} · {query.category_code.length ? query.category_code.map((code) => catalogue.categories.find((item) => item.code === code)?.label ?? code).join(", ") : "All categories"} · {query.condition_code.length ? query.condition_code.map((code) => catalogue.conditions.find((item) => item.code === code)?.label ?? code).join(", ") : "Any condition"}{query.min_price_paise || query.max_price_paise ? " · Price bounds applied" : ""}</summary><form className="discovery-form" onSubmit={submit} noValidate>
        <div className="discovery-search">
          <label htmlFor="discovery-query">Search listings
            <input id="discovery-query" type="search" value={draft.q} maxLength={240}
              placeholder="Try a bicycle, desk or textbook" onChange={(event) => change('q', event.target.value)}
              aria-describedby="discovery-query-help" />
          </label>
          <Button type="submit">Search</Button>
        </div>
        <p id="discovery-query-help" className="discovery-hint">Search titles and descriptions. Up to 120 characters.</p>
        <div className="discovery-filters">
          <MultiChoiceDropdown
            emptyLabel="All categories"
            label="Item category"
            onValuesChange={(values) => change('category_code', values)}
            options={[
              ...catalogue.categories.map((category) => ({ value: category.code, label: category.label })),
              ...draft.category_code.filter((code) => !catalogue.categories.some((category) => category.code === code))
                .map((code) => ({ value: code, label: `Unavailable category · ${code}` })),
            ]}
            values={draft.category_code}
          />
          <MultiChoiceDropdown
            emptyLabel="Any condition"
            label="Condition"
            onValuesChange={(values) => change('condition_code', values)}
            options={[
              ...catalogue.conditions.map((condition) => ({ value: condition.code, label: condition.label })),
              ...draft.condition_code.filter((code) => !catalogue.conditions.some((condition) => condition.code === code))
                .map((code) => ({ value: code, label: `Unavailable condition · ${code}` })),
            ]}
            values={draft.condition_code}
          />
          <label htmlFor="discovery-min">Minimum price (₹)
            <input id="discovery-min" type="text" inputMode="numeric" maxLength={8} value={draft.min_rupees} placeholder="No minimum"
              onChange={(event) => change('min_rupees', event.target.value)} />
          </label>
          <label htmlFor="discovery-max">Maximum price (₹)
            <input id="discovery-max" type="text" inputMode="numeric" maxLength={8} value={draft.max_rupees} placeholder="No maximum"
              onChange={(event) => change('max_rupees', event.target.value)} />
          </label>
          <label htmlFor="discovery-sort">Sort by
            <select id="discovery-sort" aria-describedby="discovery-sort-help"
              value={draft.sort}
              onChange={(event) => change('sort', event.target.value as DiscoveryForm['sort'])}>
              {draft.q.trim() && <option value="relevance">Best Match</option>}
              <option value="created_desc">Newest first</option><option value="price_asc">Price: low to high</option><option value="price_desc">Price: high to low</option>
            </select>
            <span id="discovery-sort-help" className="discovery-hint">Text searches default to Best Match: direct matches first, expanded or typo matches next, and meaning-based matches after. Browsing defaults to newest first.</span>
          </label>
          <label htmlFor="discovery-size">Listings per page
            <select id="discovery-size" value={draft.page_size} onChange={(event) => change('page_size', Number(event.target.value) as DiscoveryForm['page_size'])}>
              <option value={20}>20</option><option value={50}>50</option><option value={100}>100</option>
            </select>
          </label>
        </div>
        <div className="discovery-form-actions">
          <Button type="submit" variant="secondary">Apply filters</Button>
          <Button variant="secondary" onClick={() => { setDraft(discoveryForm(DEFAULT_QUERY)); setFormError(''); navigate(DEFAULT_QUERY); }}>Reset</Button>
          <span className="discovery-hint">Whole rupees only. ₹0 includes free items.</span>
        </div>
        {formError && <p className="discovery-error" role="alert">{formError}</p>}
      </form></details>
      <div className="discovery-results" aria-live="polite" aria-busy={result.kind === 'loading'}>
        {result.kind === 'loading' && <p className="discovery-state" role="status">Loading current listings…</p>}
        {result.kind === 'invalid' && <div className="discovery-state" role="alert"><h2>Check your search</h2><p>{result.message}</p></div>}
        {result.kind === 'error' && <div className="discovery-state" role="alert">
          <h2>{result.error.status === 401 ? 'Sign in to continue' : 'Could not load listings'}</h2>
          <p>{hybridUnavailable ? 'Search is temporarily unavailable. Please retry.' : result.error.message}</p>
          {result.error.status === 401 && <Link to="/sign-in">Go to sign in</Link>}
          <Button variant="secondary" onClick={() => setReload((value) => value + 1)}>Retry</Button>
        </div>}
        {ready && <>
          <p className="discovery-results-heading">Page {ready.page} · {ready.items.length} {ready.items.length === 1 ? 'listing' : 'listings'} on this page</p>
          {ready.items.length === 0 ? <div className="discovery-state"><h2>No listings found</h2><p>Try fewer filters or different search words.</p><Button variant="secondary" onClick={() => { setDraft(discoveryForm(DEFAULT_QUERY)); setFormError(''); navigate(DEFAULT_QUERY); }}>Clear filters</Button></div> : (
            <ul className="discovery-grid">
              {ready.items.map((listing) => <li key={listing.listing_id}>
                <SaleListingCard listing={listing}>{renderListingActions?.(listing.listing_id)}</SaleListingCard>
              </li>)}
            </ul>
          )}
          <nav className="discovery-pagination" aria-label="Listing result pages">
            <Button variant="secondary" disabled={query.page <= 1} onClick={() => navigate({ ...query, page: query.page - 1 })}>Previous</Button>
            <span>Page {query.page}</span>
            <Button variant="secondary" disabled={!ready.has_next} onClick={() => navigate({ ...query, page: query.page + 1 })}>Next</Button>
          </nav>
        </>}
      </div>
    </section>
  );
}
