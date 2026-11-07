import { ConversationOffers } from './ConversationOffers';
import { Suspense, lazy, useEffect, useState, type PropsWithChildren } from 'react';
import { Link, useLocation, useParams, useSearchParams } from 'react-router';
import { ConversationDetailPage as ConnectedConversationDetail, ConversationInboxPage } from '../features/conversations';
import { MicrosoftCallback, HandleEditor, ContactsEditor, SignIn, AccountStateBoundary, SellerEligibilityGate, useIdentity } from '../features/identity';
import { CreateListing, ListingDetail, ListingEdit, ListingImagePreview, MyListings, StartListingConversationAction, listingPrice, readListing } from '../features/listings';
import { WantedBrowse, MyWantedRequests, WantedDetail, SavedListings, SaveListingAction, SaleListingCard, SaleListingPreview, readWanted } from '../features/search';
import { SaleDiscovery } from '../features/search';
import { PageFrame, SegmentedControl } from '../shared/ui';
import { isLocalConversationDemoAllowed } from './conversationDemoGate';
import type { ConversationDemoPageProps } from './ConversationDemo';

type View = 'sales' | 'wanted';

const LazyConversationDemoPage = import.meta.env.DEV
  ? lazy(() =>
      import('./ConversationDemo').then((module) => ({ default: module.ConversationDemoPage })),
    )
  : null;

function RoutePage({ title, children, sessionScoped = true }: PropsWithChildren<{ title: string; sessionScoped?: boolean }>) {
  return (
    <PageFrame className="route-page">
      <h1>{title}</h1>
      {sessionScoped ? <AccountStateBoundary>{children}</AccountStateBoundary> : children}
    </PageFrame>
  );
}

function DevelopmentConversationDemo(props: ConversationDemoPageProps) {
  if (!LazyConversationDemoPage) return null;
  return (
    <Suspense
      fallback={
        <RoutePage title={props.page === 'inbox' ? 'My conversations' : 'Conversation'} sessionScoped={false}>
          <p role="status">Loading local conversation demo…</p>
        </RoutePage>
      }
    >
      <RoutePage title={props.page === 'inbox' ? 'My conversations' : 'Conversation'} sessionScoped={false}>
        <LazyConversationDemoPage {...props} />
      </RoutePage>
    </Suspense>
  );
}

function localConversationDemoEnabled(search: string): boolean {
  return (
    import.meta.env.DEV &&
    typeof window !== 'undefined' &&
    isLocalConversationDemoAllowed(true, window.location.hostname, search)
  );
}

export function SignInPage() {
  return (
    <PageFrame className="route-page route-page--sign-in">
      <h1>Sign in</h1>
      <SignIn />
    </PageFrame>
  );
}

export function AuthCallbackPage() {
  return (
    <RoutePage title="Authentication return" sessionScoped={false}>
      <MicrosoftCallback />
    </RoutePage>
  );
}

export function DiscoveryPage() {
  const { status, user } = useIdentity();
  // Temporary buyers may contact a seller, but only regular members may sell.
  const canContactSeller = status === 'ready' && !!user && Date.parse(user.valid_until) > Date.now();
  const canUseSellerActions = canContactSeller && user?.account_class === 'regular';
  const [view, setView] = useState<View>('sales');
  return (
    <RoutePage title="Discover">
      <section className="discovery-welcome" aria-label="Campus marketplace">
        <span className="discovery-welcome__label">The campus marketplace</span>
        <h2>A little less new. A lot more local.</h2>
        <p>Give good things a second life, right here on campus.</p>
      </section>
      <SegmentedControl
        label="Discovery view"
        options={[
          { value: 'sales', label: 'Sale Listings' },
          { value: 'wanted', label: 'Wanted Requests' },
        ]}
        value={view}
        onValueChange={setView}
      />
      {view === 'sales' ? (
        <SaleDiscovery createListingAction={canUseSellerActions
          ? <Link className="ui-button ui-button--primary" to="/listings/new">New Listing</Link>
          : null}
          renderListingActions={(listingId) => <>
            {status === 'ready'
              ? <SaveListingAction listingId={listingId} compact />
              : <Link className="ui-button ui-button--secondary" to="/sign-in">Sign in to save</Link>}
            {canContactSeller
              ? <StartListingConversationAction compact listingId={listingId} />
              : status === 'anonymous'
                ? <Link className="ui-button ui-button--secondary" to="/sign-in">Sign in to contact seller</Link>
                : <span className="discovery-action-note">Sign in to contact the seller.</span>}
          </>} />
      ) : (
        <WantedBrowse />
      )}
    </RoutePage>
  );
}

export function ListingCreatePage() {
  return (
    <RoutePage title="Create a sale listing" sessionScoped={false}>
      <SellerEligibilityGate>
        <CreateListing renderPreview={(draft) => <SaleListingPreview draft={draft} />} />
      </SellerEligibilityGate>
    </RoutePage>
  );
}

export function ListingDetailPage() {
  const { listingId } = useParams();
  return (
    <RoutePage title="Sale listing detail">
      <ListingDetail listingId={listingId}>
        <SaveListingAction listingId={listingId} />
        <StartListingConversationAction listingId={listingId} />
      </ListingDetail>
    </RoutePage>
  );
}

export function ListingEditPage() {
  const { listingId } = useParams();
  return (
    <RoutePage title="Edit a sale listing" sessionScoped={false}>
      <SellerEligibilityGate action="manage"><ListingEdit listingId={listingId} /></SellerEligibilityGate>
    </RoutePage>
  );
}

export function MyListingsPage() {
  const [params, setParams] = useSearchParams();
  const startCreatingWanted = params.get('create') === 'wanted';
  const view: View = params.get('view') === 'wanted' || startCreatingWanted ? 'wanted' : 'sales';
  useEffect(() => {
    if (!startCreatingWanted) return;
    const next = new URLSearchParams(params);
    next.delete('create');
    setParams(next, { replace: true });
  }, [startCreatingWanted, params, setParams]);
  return (
    <RoutePage title="My listings">
      <SegmentedControl
        label="My listings view"
        options={[
          { value: 'sales', label: 'Sale Listings' },
          { value: 'wanted', label: 'Wanted Requests' },
        ]}
        value={view}
        onValueChange={(nextView) => {
          const next = new URLSearchParams(params);
          next.set('view', nextView);
          next.delete('create');
          setParams(next);
        }}
      />
      {view === 'sales' ? (
        <SellerEligibilityGate action="manage"><MyListings renderListingCard={(listing, ownerActions) => (
          <SaleListingCard
            listing={listing}
            availabilityLabel={listing.availability === 'available' ? 'Your listing · Available' : 'Your listing · Unavailable'}
          >
            {ownerActions}
          </SaleListingCard>
        )} /></SellerEligibilityGate>
      ) : (
        <MyWantedRequests startCreating={startCreatingWanted} />
      )}
    </RoutePage>
  );
}

export function SavedListingsPage() {
  return (
    <RoutePage title="Saved sale listings">
      <SavedListings />
    </RoutePage>
  );
}

export function ConversationsPage() {
  const { search } = useLocation();
  if (localConversationDemoEnabled(search)) {
    return <DevelopmentConversationDemo page="inbox" />;
  }
  return (
    <RoutePage title="My conversations">
      <ConversationInboxPage renderOriginContext={(kind, originId) => (
        <ConversationOriginContext key={`${kind}:${originId}`} kind={kind} originId={originId} />
      )} />
    </RoutePage>
  );
}

/** Resolves only public sale/request fields for inbox recognition; failure never exposes an ID. */
function ConversationOriginContext({ kind, originId, threadContext = false }: {
  kind: 'sale_listing' | 'wanted_request'; originId: string; threadContext?: boolean;
}) {
  const [context, setContext] = useState<{ title: string; price?: string; imageId?: string } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setContext(null);
    const request = kind === 'sale_listing'
      ? readListing(originId, controller.signal).then((listing) => ({
          title: listing.title,
          price: listingPrice(listing.asking_price_paise),
          imageId: listing.image_ids[0],
        }))
      : readWanted(originId, controller.signal).then((wanted) => ({
          title: wanted.title,
          price: wanted.budget_paise == null ? 'Budget not stated' : `₹${(wanted.budget_paise / 100).toLocaleString('en-IN')}`,
        }));
    request.then((value) => {
      if (!controller.signal.aborted) setContext(value);
    }).catch(() => {
      if (!controller.signal.aborted) setContext({ title: kind === 'sale_listing' ? 'Sale listing details unavailable' : 'Wanted Request details unavailable' });
    });
    return () => controller.abort();
  }, [kind, originId]);
  const title = context?.title ?? (kind === 'sale_listing' ? 'Loading sale listing…' : 'Loading Wanted Request…');
  return (
    <div className={`conversation-inbox__origin-context${threadContext ? ' conversation-thread__origin-context' : ''}`}>
      {context?.imageId ? <span className="conversation-inbox__origin-photo">
        <ListingImagePreview imageId={context.imageId} alt={`Photo of ${context.title}`} compact allowRetry={false} />
      </span> : null}
      <span className="conversation-inbox__origin-summary">
        <span className="conversation-inbox__origin-title">{title}</span>
        {context?.price ? <span className="conversation-inbox__origin-price">{context.price}</span> : null}
      </span>
    </div>
  );
}

export function ConversationDetailPage() {
  const { conversationId } = useParams();
  const { search } = useLocation();
  if (localConversationDemoEnabled(search)) {
    return <DevelopmentConversationDemo conversationId={conversationId} page="thread" />;
  }
  return (
    <RoutePage title="Conversation">
      <div className="conversation-detail-layout">
        <ConnectedConversationDetail conversationId={conversationId} renderOriginContext={(kind, originId) => <ConversationOriginContext key={`${kind}:${originId}`} kind={kind} originId={originId} threadContext />} />
        <ConversationOffers key={conversationId} conversationId={conversationId} />
      </div>
    </RoutePage>
  );
}

export function AccountContactsPage() {
  const [params] = useSearchParams();
  const conversation = params.get('conversation');
  const returnPath = conversation && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(conversation)
    ? `/my/conversations/${conversation}` : null;
  return (
    <RoutePage title="Account">
      <div className="account-settings">
        <HandleEditor />
        <ContactsEditor />
        {returnPath ? <Link className="ui-button ui-button--secondary" to={returnPath}>Back to conversation</Link> : null}
      </div>
    </RoutePage>
  );
}

export function WantedRequestPage() {
  const { requestId } = useParams();
  return (
    <RoutePage title="Wanted request">
      <WantedDetail requestId={requestId} />
    </RoutePage>
  );
}

export function NotFoundPage() {
  return (
    <RoutePage title="Page not found" sessionScoped={false}>
      <p>This path is not part of the approved scaffold.</p>
    </RoutePage>
  );
}
