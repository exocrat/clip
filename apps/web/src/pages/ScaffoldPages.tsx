import { useState, type PropsWithChildren } from 'react';
import { useParams } from 'react-router';
import { ConversationsPlaceholder } from '../features/conversations';
import { ContactsEditor, SignIn, IdentityPlaceholder as IdentityFeaturePlaceholder } from '../features/identity';
import { ListingsPlaceholder as ListingsFeaturePlaceholder } from '../features/listings';
import { SearchPlaceholder as SearchFeaturePlaceholder } from '../features/search';
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
      <IdentityFeaturePlaceholder title="Authentication callback state" />
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
        <SearchFeaturePlaceholder title="Search and browse sale listings">
          <ListingsFeaturePlaceholder title="Sale listing summaries" />
        </SearchFeaturePlaceholder>
      ) : (
        <SearchFeaturePlaceholder title="Browse public wanted requests" />
      )}
    </RoutePage>
  );
}

export function ListingCreatePage() {
  return (
    <RoutePage title="Create a sale listing">
      <ListingsFeaturePlaceholder title="Sale listing form">
        <IdentityFeaturePlaceholder title="Seller eligibility connection" />
      </ListingsFeaturePlaceholder>
    </RoutePage>
  );
}

export function ListingDetailPage() {
  const { listingId } = useParams();
  return (
    <RoutePage title="Sale listing detail">
      <RouteValue name="listingId" value={listingId} />
      <ListingsFeaturePlaceholder title="Listing details">
        <SearchFeaturePlaceholder title="Save listing action" />
        <ConversationsPlaceholder title="Start or reopen a conversation" />
      </ListingsFeaturePlaceholder>
    </RoutePage>
  );
}

export function ListingEditPage() {
  const { listingId } = useParams();
  return (
    <RoutePage title="Edit a sale listing">
      <RouteValue name="listingId" value={listingId} />
      <ListingsFeaturePlaceholder title="Listing editor" />
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
        <ListingsFeaturePlaceholder title="My sale listings and their status">
          <ConversationsPlaceholder title="Seller conversations link" />
        </ListingsFeaturePlaceholder>
      ) : (
        <SearchFeaturePlaceholder title="My wanted requests and their status">
          <ListingsFeaturePlaceholder title="Possible sale matches" />
        </SearchFeaturePlaceholder>
      )}
    </RoutePage>
  );
}

export function SavedListingsPage() {
  return (
    <RoutePage title="Saved sale listings">
      <SearchFeaturePlaceholder title="Saved listings">
        <ListingsFeaturePlaceholder title="Saved listing summaries and availability" />
      </SearchFeaturePlaceholder>
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
      <RouteValue name="requestId" value={requestId} />
      <SearchFeaturePlaceholder title="Public wanted request details">
        <IdentityFeaturePlaceholder title="Regular-member response eligibility" />
        <ConversationsPlaceholder title="Contact requester" />
      </SearchFeaturePlaceholder>
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
