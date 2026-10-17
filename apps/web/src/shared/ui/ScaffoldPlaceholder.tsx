import type { PropsWithChildren } from 'react';
import './ScaffoldPlaceholder.css';

export type ScaffoldPlaceholderProps = PropsWithChildren<{
  title: string;
  owner: string;
}>;

/** Marks unfinished scaffold content and the domain responsible for it. */
export function ScaffoldPlaceholder({
  title,
  owner,
  children,
}: ScaffoldPlaceholderProps) {
  return (
    <section aria-label={`${title} placeholder`} className="scaffold-placeholder">
      <h2>{title}</h2>
      <p className="scaffold-placeholder__notice">
        Not implemented · owner: {owner}
      </p>
      {children ? (
        <div className="scaffold-placeholder__connections">{children}</div>
      ) : null}
    </section>
  );
}
