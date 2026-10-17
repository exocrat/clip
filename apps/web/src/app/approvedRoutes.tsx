import type { RouteObject } from 'react-router';
import { AppShell } from './AppShell';
import {
  AccountContactsPage,
  AuthCallbackPage,
  ConversationDetailPage,
  ConversationsPage,
  DiscoveryPage,
  ListingCreatePage,
  ListingDetailPage,
  ListingEditPage,
  MyListingsPage,
  NotFoundPage,
  SavedListingsPage,
  SignInPage,
  WantedRequestPage,
} from '../pages/ScaffoldPages';

/** The route tree used by the app and checked against the approved inventory. */
export const approvedRoutes: RouteObject[] = [
  {
    element: <AppShell />,
    children: [
      { path: '/sign-in', element: <SignInPage /> },
      { path: '/auth/callback', element: <AuthCallbackPage /> },
      { path: '/', element: <DiscoveryPage /> },
      { path: '/listings/new', element: <ListingCreatePage /> },
      { path: '/listings/:listingId/edit', element: <ListingEditPage /> },
      { path: '/listings/:listingId', element: <ListingDetailPage /> },
      { path: '/my/listings', element: <MyListingsPage /> },
      { path: '/saved', element: <SavedListingsPage /> },
      { path: '/my/conversations', element: <ConversationsPage /> },
      {
        path: '/my/conversations/:conversationId',
        element: <ConversationDetailPage />,
      },
      { path: '/account/contacts', element: <AccountContactsPage /> },
      { path: '/wanted/:requestId', element: <WantedRequestPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
];
