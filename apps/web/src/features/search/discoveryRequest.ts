import { DiscoveryApiError, readDiscoveryCatalogue, readDiscoveryPage,
  type CatalogueView, type PageResultListingSummary } from './discoveryApi';
import type { DiscoveryQuery } from './discoveryQuery';

/** Own one catalogue/page request pair. Cleanup aborts transport and ignores late
 * completion even when a transport ignores AbortSignal. Callbacks receive only
 * current results; retries start a new pair with the same applied inputs. */
export function startDiscoveryRequest(query: DiscoveryQuery,
  ready: (catalogue: CatalogueView, page: PageResultListingSummary) => void,
  failed: (error: DiscoveryApiError) => void): () => void {
  const controller = new AbortController();
  let current = true;
  Promise.all([readDiscoveryCatalogue(controller.signal), readDiscoveryPage(query, controller.signal)])
    .then(([catalogue, page]) => { if (current) ready(catalogue, page); })
    .catch((error: unknown) => {
      if (current && !controller.signal.aborted) {
        failed(error instanceof DiscoveryApiError ? error : new DiscoveryApiError(0));
        controller.abort();
      }
    });
  return () => { current = false; controller.abort(); };
}
