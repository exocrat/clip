import { useState, type PropsWithChildren } from 'react';
import { useParams } from 'react-router';
import { ConversationsPlaceholder } from '../features/conversations';
import { MicrosoftCallback, ContactsEditor, SignIn, IdentityPlaceholder as IdentityFeaturePlaceholder } from '../features/identity';
import { ListingsPlaceholder as ListingsFeaturePlaceholder } from '../features/listings';
import { CreateListing, ListingDetail, ListingEdit, MyListings } from '../features/listings';
import { WantedBrowse, MyWantedRequests, WantedDetail, SavedListings, SaveListingAction } from '../features/search';
import { SaleDiscovery } from '../features/search';
import { PageFrame, SegmentedControl } from '../shared/ui';

type View = 'sales' | 'wanted';

function RoutePage({ title, children }: PropsWithChildren<{ title: string }>) {
  return (
    <PageFrame className="route-page">
      <h1>{title}</h1>
      {children}
    </PageFrame>
  );
}

function RouteValue({ name, value }: { name: string; value?: string }) {
  return (
    <p>
      Route parameter <code>{name}</code>: <code>{value ?? 'not present'}</code>. No record is
      loaded by this scaffold.
    </p>
  );
}

export function SignInPage() {
  return (
    <RoutePage title="Sign in">
      <SignIn />
    </RoutePage>
  );
}

export function AuthCallbackPage() {
  return (
    <RoutePage title="Authentication return">
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
    <RoutePage title="Create a sale listing">
      <CreateListing>
        <IdentityFeaturePlaceholder title="Seller eligibility connection" />
      </CreateListing>
    </RoutePage>
  );
}

export function ListingDetailPage() {
  const { listingId } = useParams();
  return (
    <RoutePage title="Sale listing detail">
      <ListingDetail listingId={listingId}>
        <SaveListingAction listingId={listingId} />
        <ConversationsPlaceholder title="Start or reopen a conversation" />
      </ListingDetail>
    </RoutePage>
  );
}

export function ListingEditPage() {
  const { listingId } = useParams();
  return (
    <RoutePage title="Edit a sale listing">
      <ListingEdit listingId={listingId} />
    </RoutePage>
  );
}

export function MyListingsPage() {
  const [view, setView] = useState<View>('sales');
  return (
    <RoutePage title="My listings">
      <SegmentedControl
        label="My listings view"
        options={[
          { value: 'sales', label: 'Sale Listings' },
          { value: 'wanted', label: 'Wanted Requests' },
        ]}
        value={view}
        onValueChange={setView}
      />
      {view === 'sales' ? (
        <MyListings />
      ) : (
        <MyWantedRequests />
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
  return (
    <RoutePage title="My conversations">
      <ConversationsPlaceholder title="Buyer and seller conversation views">
        <ListingsFeaturePlaceholder title="Listing and request context" />
      </ConversationsPlaceholder>
    </RoutePage>
  );
}

export function ConversationDetailPage() {
  const { conversationId } = useParams();
  return (
    <RoutePage title="Conversation">
      <RouteValue name="conversationId" value={conversationId} />
      <ConversationsPlaceholder title="Private conversation and offer controls">
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
    <RoutePage title="Page not found">
      <p>This path is not part of the approved scaffold.</p>
    </RoutePage>
  );
}
