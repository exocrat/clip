import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Link, useNavigate } from 'react-router';
import type {
  DraftMatchResult,
  PageResultSavedListingView,
  PageResultWantedRequestOwnerView,
  PageResultWantedRequestPublic,
} from '../../../../../contracts/generated/types.gen';
import { Button } from '../../shared/ui';
import { discoveryPrice, readDiscoveryCatalogue, type ListingSummary } from './discoveryApi';
import { SaleListingCard } from './SaleListingCard';
import {
  browseWanted,
  budgetPaise,
  changeWantedState,
  contactRequester,
  createWanted,
  draftMatches,
  editWanted,
  isListingSaved,
  ownWanted,
  readSaved,
  readSearchSession,
  readWanted,
  saveListing,
  SearchIntent,
  unsaveListing,
  validSearchId,
  wantedPreviewActive,
  WantedApiError,
  type WantedRequestOwnerView,
  type WantedRequestPublic,
} from './wantedApi';
import './wanted.css';

/** Local request state is keyed to its inputs so stale/private results never flash on navigation. */
function useRead<T>(key: string, load: (signal: AbortSignal) => Promise<T>) {
  const [attempt, setAttempt] = useState(0);
  const token = `${key}:${attempt}`;
  const [state, setState] = useState<{ token: string; data?: T; error?: string }>({ token: '' });
  const loader = useRef(load);
  loader.current = load;
  useEffect(() => {
    const controller = new AbortController();
    loader
      .current(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ token, data });
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted) setState({ token, error: error.message });
      });
    return () => controller.abort();
  }, [token]);
  return { ...(state.token === token ? state : {}), retry: () => setAttempt((v) => v + 1) };
}
/** A test server identifies itself explicitly; normal runtime never inherits this disclosure. */
function PreviewNotice() {
  return wantedPreviewActive() ? (
    <p role="note">
      Isolated local preview: real Search database and draft queries; synthetic Identity and saved-listing
      snapshots. Conversations and image delivery are unavailable. No cloud services.
    </p>
  ) : null;
}
/** Accessible loading/error state with an explicit read retry; never retries a write. */
function ReadState({ error, retry, children }: { error?: string; retry: () => void; children?: ReactNode }) {
  return error ? (
    <div role="alert">
      <p>{error}</p>
      <Button onClick={retry}>Retry loading</Button>
    </div>
  ) : (
    (children ?? <p role="status">Loading…</p>)
  );
}
/** Bound previous/next navigation to the server page and lookahead result. */
function Pages({
  number,
  hasNext,
  onChange,
}: {
  number: number;
  hasNext: boolean;
  onChange: (value: number) => void;
}) {
  return (
    <nav aria-label="Results pages">
      <Button disabled={number === 1} onClick={() => onChange(number - 1)}>
        Previous
      </Button>
      <span> Page {number} </span>
      <Button disabled={!hasNext} onClick={() => onChange(number + 1)}>
        Next
      </Button>
    </nav>
  );
}
/** Render the public request fields and optional owner actions in one card. */
function RequestCard({ item, children }: { item: WantedRequestPublic; children?: ReactNode }) {
  return (
    <article className="wanted-card">
      <div className="wanted-card__head">
        <span className="wanted-card__category">Wanted · {item.category_label}</span>
        <span className="wanted-card__budget">
          {item.budget_paise == null ? 'Budget not stated' : discoveryPrice(item.budget_paise)}
        </span>
      </div>
      <h3><Link to={`/wanted/${item.request_id}`}>{item.title}</Link></h3>
      <p className="wanted-description">{item.description}</p>
      {children}
    </article>
  );
}

/** Authenticated public requests contain no author identity or private contact information. */
export function WantedBrowse() {
  const [number, setNumber] = useState(1);
  const result = useRead<PageResultWantedRequestPublic>(`public:${number}`, (signal) =>
    browseWanted(number, signal),
  );
  return (
    <section className="wanted-feature">
      <PreviewNotice />
      <h2>Wanted requests</h2>
      <p>
        Open requests from the campus community. <Link to="/my/listings">Manage your wanted requests</Link>.
      </p>
      <ReadState error={result.error} retry={result.retry}>
        {result.data && (
          <>
            {!result.data.items.length && <p>No open wanted requests.</p>}
            {!!result.data.items.length && <ul className="wanted-grid">
              {result.data.items.map((item) => (
                <li key={item.request_id}><RequestCard item={item} /></li>
              ))}
            </ul>}
            <Pages number={number} hasNext={result.data.has_next} onChange={setNumber} />
          </>
        )}
      </ReadState>
    </section>
  );
}

/** Match only the current draft title; failure or no matches never disables submission. */
function DraftSuggestions({ title }: { title: string }) {
  const trimmed = title.trim();
  const [attempt, setAttempt] = useState(0);
  const key = `${trimmed}:${attempt}`;
  const [state, setState] = useState<{ key: string; data?: DraftMatchResult; error?: string }>({ key: '' });
  useEffect(() => {
    if (!trimmed || [...trimmed].length > 120) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      draftMatches(trimmed, controller.signal)
        .then((data) => {
          if (!controller.signal.aborted) setState({ key, data });
        })
        .catch((error: Error) => {
          if (!controller.signal.aborted) setState({ key, error: error.message });
        });
    }, 350);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [key, trimmed]);
  if (!trimmed || [...trimmed].length > 120) return <p>Enter a title to see possible sale matches.</p>;
  const current = state.key === key ? state : undefined;
  return (
    <aside aria-label="Possible sale matches">
      <h3>Possible sale matches</h3>
      <p>
        Matches use the title only, without your category or budget. They may not suit your needs; you can
        publish independently.
      </p>
      {current?.error ? (
        <div role="status">
          <p>Possible matches could not be loaded. You can still publish.</p>
          <Button onClick={() => setAttempt((v) => v + 1)}>Retry matches</Button>
        </div>
      ) : !current?.data ? (
        <p role="status">Looking for possible matches…</p>
      ) : (
        <>
          {!current.data.items.length && <p>No possible matches found.</p>}
          <ul>
            {current.data.items.map((item) => (
              <li key={item.listing_id}>
                <Link to={`/listings/${item.listing_id}`} target="_blank" rel="noreferrer">
                  {item.title} (opens in new tab)
                </Link>{' '}
                · {discoveryPrice(item.asking_price_paise)}
              </li>
            ))}
          </ul>
          {current.data.has_more && <p>More matches may be available in discovery.</p>}
        </>
      )}
    </aside>
  );
}

/** Owner editor keeps failed drafts and retry keys in memory only; revisions protect concurrent edits. */
function WantedEditor({
  initial,
  onSaved,
  onCancel,
}: {
  initial?: WantedRequestOwnerView;
  onSaved: (value: WantedRequestOwnerView) => void;
  onCancel?: () => void;
}) {
  const [title, setTitle] = useState(initial?.title ?? '');
  const [description, setDescription] = useState(initial?.description ?? '');
  const [category, setCategory] = useState(initial?.category_code ?? '');
  const [budget, setBudget] = useState(
    initial?.budget_paise == null ? '' : String(initial.budget_paise / 100),
  );
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const categories = useRead('catalogue', readDiscoveryCatalogue);
  const intent = useRef(new SearchIntent());
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setError('');
    try {
      if (
        ![...title.trim()].length ||
        [...title.trim()].length > 120 ||
        !description.trim() ||
        [...description.trim()].length > 5000
      )
        throw new Error('Enter a title (up to 120 characters) and description (up to 5,000 characters).');
      if (!category || !categories.data?.categories.some((value) => value.code === category))
        throw new Error('Choose a current category.');
      const fields = {
        title: title.trim(),
        description: description.trim(),
        category_code: category,
        budget_paise: budgetPaise(budget),
      };
      const body = { ...fields, ...(initial ? { expected_revision: initial.revision } : {}) };
      const operation_id = intent.current.key(body);
      const controller = new AbortController();
      active.current = controller;
      setBusy(true);
      const value = initial
        ? await editWanted(
            initial.request_id,
            { ...fields, expected_revision: initial.revision, operation_id },
            controller.signal,
          )
        : await createWanted({ ...fields, operation_id }, controller.signal);
      if (!controller.signal.aborted) {
        intent.current.clear();
        onSaved(value);
      }
    } catch (failure) {
      if (!active.current?.signal.aborted) setError((failure as Error).message);
    } finally {
      if (!active.current?.signal.aborted) setBusy(false);
    }
  }
  return (
    <section>
      <h3>{initial ? 'Edit wanted request' : 'Create wanted request'}</h3>
      <form onSubmit={submit}>
        <fieldset disabled={busy}>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label>
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              rows={5}
            />
          </label>
          <label>
            Category
            <select value={category} onChange={(e) => setCategory(e.target.value)} required>
              <option value="">Choose a category</option>
              {initial &&
                !categories.data?.categories.some((value) => value.code === initial.category_code) && (
                  <option value={initial.category_code} disabled>
                    {initial.category_label} (choose a current category)
                  </option>
                )}
              {categories.data?.categories.map((value) => (
                <option key={value.code} value={value.code}>
                  {value.label}
                </option>
              ))}
            </select>
          </label>
          <ReadState error={categories.error} retry={categories.retry}>
            {categories.data && <span />}
          </ReadState>
          <label>
            Optional budget (whole ₹)
            <input
              inputMode="numeric"
              maxLength={16}
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              aria-describedby="wanted-budget-help"
            />
          </label>
          <p id="wanted-budget-help">Leave blank for no stated budget; enter 0 for free.</p>
          {error && <p role="alert">{error}</p>}
          <Button type="submit">{busy ? 'Saving…' : initial ? 'Save changes' : 'Publish request'}</Button>
          {onCancel && (
            <Button variant="secondary" onClick={onCancel}>
              Cancel editing
            </Button>
          )}
        </fieldset>
      </form>
      <DraftSuggestions title={title} />
    </section>
  );
}

/** The private owner list is the only UI source of edit/availability controls. */
export function MyWantedRequests() {
  const [number, setNumber] = useState(1);
  const [version, setVersion] = useState(0);
  const [editing, setEditing] = useState<WantedRequestOwnerView>();
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState('');
  const result = useRead<PageResultWantedRequestOwnerView>(`own:${number}:${version}`, (signal) =>
    ownWanted(number, signal),
  );
  function saved() {
    setEditing(undefined);
    setCreating(false);
    setVersion((v) => v + 1);
    setMessage('Your wanted request has been saved.');
  }
  return (
    <section className="wanted-feature">
      <PreviewNotice />
      <h2>My wanted requests</h2>
      <p>Only you can edit these requests or change their availability.</p>
      {message && <p role="status">{message}</p>}
      {creating || editing ? (
        <WantedEditor
          key={editing ? `${editing.request_id}:${editing.revision}` : 'new'}
          initial={editing}
          onSaved={saved}
          onCancel={() => {
            setCreating(false);
            setEditing(undefined);
          }}
        />
      ) : (
        <>
          <Button
            onClick={() => {
              setMessage('');
              setCreating(true);
            }}
          >
            Create wanted request
          </Button>
          <Button variant="secondary" onClick={result.retry}>
            Refresh requests
          </Button>
          <ReadState error={result.error} retry={result.retry}>
            {result.data && (
              <>
                {!result.data.items.length && <p>You have no wanted requests.</p>}
                {!!result.data.items.length && <ul className="wanted-grid wanted-grid--owner">
                  {result.data.items.map((item) => (
                    <li key={`${item.request_id}:${item.revision}`}>
                      <RequestCard item={item}>
                        <p className="wanted-card__status">Status: {item.state === 'open' ? 'Open' : 'Unavailable'}</p>
                        <div className="wanted-card__actions">
                          <Button aria-label={`Edit ${item.title}`} onClick={() => setEditing(item)}>Edit request</Button>
                          <Availability item={item} onChanged={() => setVersion((v) => v + 1)} />
                        </div>
                      </RequestCard>
                    </li>
                  ))}
                </ul>}
                <Pages number={number} hasNext={result.data.has_next} onChange={setNumber} />
              </>
            )}
          </ReadState>
        </>
      )}
    </section>
  );
}

/** State changes retain revision/key after an unknown result; reload resolves stale revisions. */
function Availability({ item, onChanged }: { item: WantedRequestOwnerView; onChanged: () => void }) {
  const intent = useRef(new SearchIntent());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  async function change() {
    if (busy) return;
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    setError('');
    const body = {
      expected_revision: item.revision,
      state: item.state === 'open' ? ('unavailable' as const) : ('open' as const),
    };
    try {
      await changeWantedState(
        item.request_id,
        { ...body, operation_id: intent.current.key(body) },
        controller.signal,
      );
      if (!controller.signal.aborted) onChanged();
    } catch (failure) {
      if (!controller.signal.aborted) setError((failure as Error).message);
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return (
    <div>
      <Button disabled={busy} onClick={change}>
        {busy ? 'Updating…' : item.state === 'open' ? 'Mark unavailable' : 'Reopen request'}
      </Button>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}

/** Detail never exposes author contacts; only a confirmed backend conversation result navigates. */
export function WantedDetail({ requestId }: { requestId?: string }) {
  return validSearchId(requestId) ? (
    <WantedDetailRecord key={requestId} requestId={requestId} />
  ) : (
    <p role="alert">This wanted request link is invalid.</p>
  );
}
/** Load current detail/session, expire capability and navigate only on confirmed success. */
function WantedDetailRecord({ requestId }: { requestId: string }) {
  const result = useRead(`request:${requestId}`, (signal) => readWanted(requestId, signal));
  const session = useRead('session', readSearchSession);
  const navigate = useNavigate();
  const intent = useRef(new SearchIntent());
  const active = useRef<AbortController | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [expired, setExpired] = useState(false);
  useEffect(() => () => active.current?.abort(), []);
  useEffect(() => {
    if (!session.data) return;
    const timer = window.setTimeout(
      () => setExpired(true),
      Math.max(0, Math.min(2147483647, Date.parse(session.data.valid_until) - Date.now())),
    );
    return () => window.clearTimeout(timer);
  }, [session.data]);
  const regular =
    !expired &&
    session.data?.account_class === 'regular' &&
    Date.parse(session.data.valid_until) > Date.now();
  async function contact() {
    if (busy || !regular) return;
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    setError('');
    try {
      const value = await contactRequester(requestId, intent.current.key({ requestId }), controller.signal);
      if (!controller.signal.aborted) navigate(`/my/conversations/${value.conversation_id}`);
    } catch (failure) {
      if (!controller.signal.aborted) setError((failure as Error).message);
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  const unavailable = result.data && 'state' in result.data && result.data.state === 'unavailable';
  return (
    <section className="wanted-feature">
      <PreviewNotice />
      <ReadState error={result.error} retry={result.retry}>
        {result.data && (
          <>
            <RequestCard item={result.data} />
            {unavailable ? (
              <p>
                This request is unavailable. You can manage it in{' '}
                <Link to="/my/listings">My wanted requests</Link>.
              </p>
            ) : (
              <>
                <ReadState error={session.error} retry={session.retry}>
                  {session.data && (
                    <p>
                      {expired
                        ? 'Your session has expired. Sign in again.'
                        : regular
                          ? 'Eligible regular members can start or reopen a private conversation. Your own request cannot be contacted.'
                          : 'Temporary accounts can browse requests; responding requires a regular account.'}
                    </p>
                  )}
                </ReadState>
                <Button disabled={!regular || busy} onClick={contact}>
                  {busy ? 'Opening conversation…' : 'Contact requester'}
                </Button>
                {error && <p role="alert">{error}</p>}
              </>
            )}
          </>
        )}
      </ReadState>
    </section>
  );
}

/** Save controls acknowledge only a confirmed server result; identical uncertain retries reuse their key. */
export function SaveListingAction({ listingId }: { listingId?: string }) {
  return validSearchId(listingId) ? <SaveAction key={listingId} listingId={listingId} /> : null;
}
/** One route-scoped in-memory save intent; a lost response leaves an explicit retry. */
function SaveAction({ listingId }: { listingId: string }) {
  const intent = useRef(new SearchIntent());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [alreadySaved, setAlreadySaved] = useState(false);
  const [checkingSaved, setCheckingSaved] = useState(true);
  const [unavailable, setUnavailable] = useState(false);
  const active = useRef<AbortController | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    active.current = controller;
    isListingSaved(listingId, controller.signal).then((exists) => {
      if (!controller.signal.aborted) {
        setSaved(exists);
        setAlreadySaved(exists);
      }
    }).catch(() => {
      if (!controller.signal.aborted)
        setError('We couldn’t check your saved listings. You can retry Save safely.');
    }).finally(() => {
      if (!controller.signal.aborted) setCheckingSaved(false);
    });
    return () => controller.abort();
  }, [listingId]);
  async function save() {
    if (busy || checkingSaved || saved || unavailable) return;
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    setError('');
    try {
      await saveListing(listingId, intent.current.key({ listingId }), controller.signal);
      if (!controller.signal.aborted) {
        setSaved(true);
      }
    } catch (failure) {
      if (!controller.signal.aborted) {
        if (failure instanceof WantedApiError && failure.status === 404) {
          setUnavailable(true);
          setError('This listing can’t be saved because it is no longer available. Check Discover for current listings.');
        } else {
          setError((failure as Error).message);
        }
      }
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return (
    <section className="wanted-save-card" aria-label="Save this listing">
      <div>
        <h3>Want to come back to this?</h3>
        <p>Save it privately and find it later in your saved listings.</p>
      </div>
      <div className="wanted-save-card__actions">
        <Button disabled={checkingSaved || busy || saved || unavailable} onClick={save}>
          {checkingSaved ? 'Checking saved status…' : saved ? 'Already saved' : unavailable ? 'Unavailable to save' : busy ? 'Saving…' : error ? 'Try saving again' : 'Save listing'}
        </Button>
        <Link className="ui-button ui-button--secondary wanted-save-card__link" to="/saved">Manage saved listings</Link>
      </div>
      {alreadySaved && <p className="wanted-save-card__success" role="status">This listing is already in your saved listings.</p>}
      {saved && !alreadySaved && <p className="wanted-save-card__success" role="status">Saved to your private saved listings.</p>}
      {error && <p className="wanted-save-card__error" role="alert">{error}</p>}
    </section>
  );
}

/** Saved content is fetched privately and afresh; retired origins render a content-free placeholder. */
export function SavedListings() {
  const [number, setNumber] = useState(1);
  const [version, setVersion] = useState(0);
  const result = useRead<PageResultSavedListingView>(`saved:${number}:${version}`, (signal) =>
    readSaved(number, signal),
  );
  return (
    <section className="wanted-feature">
      <PreviewNotice />
      <h2>Your private saved listings</h2>
      <ReadState error={result.error} retry={result.retry}>
        {result.data && (
          <>
            {!result.data.items.length && (
              <p>
                No saved listings on this page. <Link to="/">Discover listings</Link>.
              </p>
            )}
            {!!result.data.items.length && <ul className="discovery-grid saved-listings-grid">
              {result.data.items.map((item) => (
                <li key={item.listing_id}>
                  {item.retired || !item.listing ? (
                    <article className="wanted-card"><h3>Retired listing — details removed</h3>
                      <RemoveSaved listingId={item.listing_id} onRemoved={() => setVersion((v) => v + 1)} />
                    </article>
                  ) : (
                    <SaleListingCard
                      listing={item.listing}
                      availabilityLabel={savedAvailability(item.listing)}
                    >
                      <RemoveSaved listingId={item.listing_id} onRemoved={() => setVersion((v) => v + 1)} />
                    </SaleListingCard>
                  )}
                </li>
              ))}
            </ul>}
            <Pages number={number} hasNext={result.data.has_next} onChange={setNumber} />
          </>
        )}
      </ReadState>
    </section>
  );
}

/** Explain why an owned saved reference may no longer appear in Discover. */
function savedAvailability(listing: ListingSummary): string {
  if (listing.availability === 'unavailable') return 'Seller marked unavailable';
  if (Date.parse(listing.available_from) > Date.now()) return 'Availability has not started';
  if (listing.available_until && Date.parse(listing.available_until) <= Date.now())
    return 'Availability has ended';
  return 'Seller marked available';
}
/** Idempotent removal refreshes private results only after a confirmed response. */
function RemoveSaved({ listingId, onRemoved }: { listingId: string; onRemoved: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  async function remove() {
    if (busy) return;
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    setError('');
    try {
      await unsaveListing(listingId, controller.signal);
      if (!controller.signal.aborted) onRemoved();
    } catch (failure) {
      if (!controller.signal.aborted) setError((failure as Error).message);
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return (
    <div>
      <Button disabled={busy} onClick={remove}>
        {busy ? 'Removing…' : 'Remove from saved'}
      </Button>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
