import type { PropsWithChildren } from 'react';
import { ScaffoldPlaceholder } from '../../shared/ui';

export type SearchPlaceholderProps = PropsWithChildren<{
  title: string;
}>;

/** Public Search/Wanted/Saved placeholder for discovery and saved views. */
export function SearchPlaceholder({
  title,
  children,
}: SearchPlaceholderProps) {
  return (
    <ScaffoldPlaceholder
      title={title}
      owner="C — Search, Wanted Requests, and Saved Listings (SE-01/SE-02)"
    >
      {children}
    </ScaffoldPlaceholder>
  );
}
