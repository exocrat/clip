import type { PropsWithChildren } from 'react';
import { ScaffoldPlaceholder } from '../../shared/ui';

export type IdentityPlaceholderProps = PropsWithChildren<{
  title: string;
}>;

/** Public Identity-owned placeholder for pages and account-related connections. */
export function IdentityPlaceholder({
  title,
  children,
}: IdentityPlaceholderProps) {
  return (
    <ScaffoldPlaceholder title={title} owner="A — Identity (ID-01)">
      {children}
    </ScaffoldPlaceholder>
  );
}
