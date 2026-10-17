import type { PropsWithChildren } from 'react';
import { ScaffoldPlaceholder } from '../../shared/ui';

export type ListingsPlaceholderProps = PropsWithChildren<{
  title: string;
}>;

/** Public Listings-owned placeholder for sale-listing and image surfaces. */
export function ListingsPlaceholder({
  title,
  children,
}: ListingsPlaceholderProps) {
  return (
    <ScaffoldPlaceholder title={title} owner="B — Listings (LI-01/LI-02)">
      {children}
    </ScaffoldPlaceholder>
  );
}
