import { Suspense, lazy, useEffect, useState, type PropsWithChildren } from 'react';
import { useLocation, useParams, useSearchParams } from 'react-router';
import { ConversationDetailPage as ConnectedConversationDetail, ConversationInboxPage, ConversationsPlaceholder } from '../features/conversations';
import { MicrosoftCallback, ContactsEditor, SignIn, AccountStateBoundary, SellerEligibilityGate, IdentityPlaceholder as IdentityFeaturePlaceholder } from '../features/identity';
import { ListingsPlaceholder as ListingsFeaturePlaceholder } from '../features/listings';
import { CreateListing, ListingDetail, ListingEdit, MyListings, StartListingConversationAction } from '../features/listings';
import { WantedBrowse, MyWantedRequests, WantedDetail, SavedListings, SaveListingAction, SaleListingPreview } from '../features/search';
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
    <RoutePage title="Sign in" sessionScoped={false}>
      <SignIn />
    </RoutePage>
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
  const [view, setView] = useState<View>('sales');
  return (
    <RoutePage title="Discover">
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
        <SaleDiscovery />
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
        <SellerEligibilityGate action="manage"><MyListings /></SellerEligibilityGate>
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
      <ConversationInboxPage />
    </RoutePage>
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
      <ConnectedConversationDetail conversationId={conversationId} />
      <ConversationsPlaceholder title="Offer, listing selection, and contact sharing">
        <ListingsFeaturePlaceholder title="Listing selection and availability" />
        <IdentityFeaturePlaceholder title="Contact options for deliberate sharing" />
      </ConversationsPlaceholder>
    </RoutePage>
  );
}

export function AccountContactsPage() {
  return (
    <RoutePage title="My contact details">
      <ContactsEditor />
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
