import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router';
import { Button } from '../../shared/ui';
import { type DiscoveryApiError, discoveryPrice, discoveryPreviewBackend,
  type CatalogueView, type PageResultListingSummary } from './discoveryApi';
import { applyDiscoveryForm, DEFAULT_QUERY, discoveryForm, discoveryParams,
  parseDiscoveryQuery, switchDiscoveryMode, type DiscoveryForm, type DiscoveryQuery } from './discoveryQuery';
import { startDiscoveryRequest } from './discoveryRequest';
import './discovery.css';

type ResultState = { kind: 'loading' } | { kind: 'ready'; page: PageResultListingSummary }
  | { kind: 'error'; error: DiscoveryApiError } | { kind: 'invalid'; message: string };

/** Own discovery state inside Search; other domains supply only reviewed public data. */
export function SaleDiscovery() {
  const [params, setParams] = useSearchParams();
  const key = params.toString();
  const parsed = useMemo(() => {
    try { return { query: parseDiscoveryQuery(new URLSearchParams(key)) }; }
    catch (error) { return { message: error instanceof Error ? error.message : 'Check the filters in this URL.' }; }
  }, [key]);
  const query = parsed.query ?? DEFAULT_QUERY;
  const [draft, setDraft] = useState<DiscoveryForm>(() => discoveryForm(query));
  const [formError, setFormError] = useState('');
  const [catalogue, setCatalogue] = useState<CatalogueView>({ categories: [], conditions: [] });
  const [requestResult, setRequestResult] = useState<{ key: string; reload: number; value: ResultState }>({ key, reload: 0, value: { kind: 'loading' } });
  const preserveDraftFor = useRef<string | null>(null);
  const [reload, setReload] = useState(0);

  // Only an explicit mode action preserves drafts. History/manual URLs resync them.
  useEffect(() => {
    if (preserveDraftFor.current === key) { preserveDraftFor.current = null; return; }
    preserveDraftFor.current = null;
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
    setDraft((previous) => ({ ...previous, [field]: value }));
    setFormError('');
  }

  /** Apply all controls together, validating exact rupees and resetting pagination. */
  function submit(event: FormEvent) {
    event.preventDefault();
    try {
      const next = discoveryParams(applyDiscoveryForm(draft, query.search_mode));
      setFormError('');
      if (next.toString() === key) setReload((value) => value + 1);
      else setParams(next);
    } catch (error) { setFormError(error instanceof Error ? error.message : 'Check your filters.'); }
  }

  /** Page navigation keeps applied filters; resetting clears every filter at once. */
  function navigate(next: DiscoveryQuery) {
    const nextParams = discoveryParams(next);
    if (nextParams.toString() === key) setReload((value) => value + 1);
    else setParams(nextParams);
  }

  /** Immediate mode changes preserve unsaved edits; only applied inputs are sent. */
  function changeMode(mode: DiscoveryQuery['search_mode']) {
    if (!parsed.query || mode === query.search_mode) return;
    const next = switchDiscoveryMode(query, mode);
    preserveDraftFor.current = discoveryParams(next).toString();
    navigate(next);
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
      <div className="discovery-mode">
        <label htmlFor="discovery-mode">Search mode
          <select id="discovery-mode" value={query.search_mode} disabled={!parsed.query}
            aria-describedby="discovery-mode-help" onChange={(event) => changeMode(event.target.value as DiscoveryQuery['search_mode'])}>
            <option value="keyword">Keyword</option><option value="hybrid">Hybrid</option>
          </select>
        </label>
        <p id="discovery-mode-help" className="discovery-hint">
          {query.search_mode === 'keyword' ? 'Matches words and known item terms, with limited typo tolerance.' : 'Adds related meanings to keyword matches.'}
          {!query.q && ' Hybrid takes effect when search text is entered.'}
        </p>
      </div>
      <form className="discovery-form" onSubmit={submit} noValidate>
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
          <label htmlFor="discovery-category">Item category
            <select id="discovery-category" value={draft.category_code} onChange={(event) => change('category_code', event.target.value)}>
              <option value="">All categories</option>
              {draft.category_code && !catalogue.categories.some((item) => item.code === draft.category_code) && <option value={draft.category_code}>Selected category (check availability)</option>}
              {catalogue.categories.map((category) => <option key={category.code} value={category.code}>{category.label}</option>)}
            </select>
          </label>
          <label htmlFor="discovery-condition">Condition
            <select id="discovery-condition" value={draft.condition_code} onChange={(event) => change('condition_code', event.target.value)}>
              <option value="">Any condition</option>
              {draft.condition_code && !catalogue.conditions.some((item) => item.code === draft.condition_code) && <option value={draft.condition_code}>Selected condition (check availability)</option>}
              {catalogue.conditions.map((condition) => <option key={condition.code} value={condition.code}>{condition.label}</option>)}
            </select>
          </label>
          <label htmlFor="discovery-min">Minimum price (₹)
            <input id="discovery-min" type="text" inputMode="numeric" value={draft.min_rupees} placeholder="No minimum"
              onChange={(event) => change('min_rupees', event.target.value)} />
          </label>
          <label htmlFor="discovery-max">Maximum price (₹)
            <input id="discovery-max" type="text" inputMode="numeric" value={draft.max_rupees} placeholder="No maximum"
              onChange={(event) => change('max_rupees', event.target.value)} />
          </label>
          <label htmlFor="discovery-negotiable">Negotiability
            <select id="discovery-negotiable" value={draft.negotiable} onChange={(event) => change('negotiable', event.target.value as DiscoveryForm['negotiable'])}>
              <option value="">Any</option><option value="true">Negotiable</option><option value="false">Fixed price</option>
            </select>
          </label>
          <label htmlFor="discovery-sort">Sort by
            <select id="discovery-sort" aria-describedby="discovery-sort-help" value={draft.sort} onChange={(event) => change('sort', event.target.value as DiscoveryForm['sort'])}>
              <option value="created_desc">Newest first</option><option value="price_asc">Price: low to high</option><option value="price_desc">Price: high to low</option>
              <option value="relevance" disabled={!draft.q.trim()}>Relevance</option>
            </select>
            <span id="discovery-sort-help" className="discovery-hint">Orders matches using the selected search mode. Relevance requires search text.</span>
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
      </form>
      <div className="discovery-results" aria-live="polite" aria-busy={result.kind === 'loading'}>
        {result.kind === 'loading' && <p className="discovery-state" role="status">Loading current listings…</p>}
        {result.kind === 'invalid' && <div className="discovery-state" role="alert"><h2>Check your search</h2><p>{result.message}</p></div>}
        {result.kind === 'error' && <div className="discovery-state" role="alert">
          <h2>{result.error.status === 401 ? 'Sign in to continue' : 'Could not load listings'}</h2>
          <p>{hybridUnavailable ? 'Hybrid search is temporarily unavailable. Retry or use Keyword.' : result.error.message}</p>
          {hybridUnavailable && <Button variant="secondary" onClick={() => changeMode('keyword')}>Use Keyword</Button>}
          {result.error.status === 401 && <Link to="/sign-in">Go to sign in</Link>}
          <Button variant="secondary" onClick={() => setReload((value) => value + 1)}>Retry</Button>
        </div>}
        {ready && <>
          <p className="discovery-results-heading">Page {ready.page} · {ready.items.length} {ready.items.length === 1 ? 'listing' : 'listings'} on this page</p>
          {ready.items.length === 0 ? <div className="discovery-state"><h2>No listings found</h2><p>Try fewer filters or different search words.</p><Button variant="secondary" onClick={() => { setDraft(discoveryForm(DEFAULT_QUERY)); setFormError(''); navigate(DEFAULT_QUERY); }}>Clear filters</Button></div> : (
            <ul className="discovery-grid">
              {ready.items.map((listing) => <li key={listing.listing_id}><article className="discovery-card">
                <p className="discovery-category">{listing.category_label}</p>
                <h2><Link to={`/listings/${listing.listing_id}`}>{listing.title}</Link></h2>
                <p className="discovery-price">{listing.asking_price_paise === 0 ? 'Free' : discoveryPrice(listing.asking_price_paise)}</p>
                <p className="discovery-description">{listing.description}</p>
                <p className="discovery-card-meta">{listing.condition_label} · {listing.negotiable ? 'Negotiable' : 'Fixed price'}</p>
                {listing.pickup_area && <p className="discovery-card-meta">Pickup: {listing.pickup_area}</p>}
                {listing.sensitive_purchase && <p className="discovery-sensitive">Sensitive purchase</p>}
                <Link className="discovery-detail" aria-label={`View ${listing.title}`} to={`/listings/${listing.listing_id}`}>View listing <span aria-hidden="true">→</span></Link>
              </article></li>)}
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
