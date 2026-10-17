import type { PropsWithChildren } from 'react';
import './PageFrame.css';

export type PageFrameProps = PropsWithChildren<{
  className?: string;
}>;

/** Provides the shared main-content width and spacing for a route page. */
export function PageFrame({ children, className = '' }: PageFrameProps) {
  const classes = ['page-frame', className].filter(Boolean).join(' ');

  return <main className={classes}>{children}</main>;
}
