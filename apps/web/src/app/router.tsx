import { BrowserRouter, useRoutes } from 'react-router';
import { approvedRoutes } from './approvedRoutes';

function RouteTree() {
  return useRoutes(approvedRoutes);
}

/** Defines the approved product paths and places each inside the shared shell. */
export function AppRouter() {
  return (
    <BrowserRouter>
      <RouteTree />
    </BrowserRouter>
  );
}
