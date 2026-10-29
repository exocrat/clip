// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { useConversationUnreadCount } from '../src/features/conversations/ConversationUnreadBadge';
function Probe({ userId }: { userId: string | null }) {
  const count = useConversationUnreadCount(userId);
  return <output aria-label="Unread count">{count ?? 'unknown'}</output>;
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
it('discards a late unread response from the previous account and clears on logout', async () => {
  const replies: Array<(value: Response) => void> = [];
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((resolve) => replies.push(resolve))));
  const { rerender } = render(<Probe userId="first" />);
  await vi.waitFor(() => expect(replies.length).toBe(1));
  rerender(<Probe userId="second" />);
  expect(screen.getByLabelText('Unread count').textContent).toBe('unknown');
  await vi.waitFor(() => expect(replies.length).toBe(2));
  replies[0](new Response(JSON.stringify({ unread_count: 99 }), { headers: { 'Content-Type': 'application/json' } }));
  replies[1](new Response(JSON.stringify({ unread_count: 2 }), { headers: { 'Content-Type': 'application/json' } }));
  await vi.waitFor(() => expect(screen.getByLabelText('Unread count').textContent).toBe('2'));
  rerender(<Probe userId={null} />);
  expect(screen.getByLabelText('Unread count').textContent).toBe('unknown');
});
