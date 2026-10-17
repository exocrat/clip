import type { PropsWithChildren } from 'react';
import { ScaffoldPlaceholder } from '../../shared/ui';

export type ConversationsPlaceholderProps = PropsWithChildren<{
  title: string;
}>;

/** Public Conversations/Offers placeholder for inbox, thread, and contact actions. */
export function ConversationsPlaceholder({
  title,
  children,
}: ConversationsPlaceholderProps) {
  return (
    <ScaffoldPlaceholder
      title={title}
      owner="D — Conversations and Offers (CN-01/CN-02)"
    >
      {children}
    </ScaffoldPlaceholder>
  );
}
