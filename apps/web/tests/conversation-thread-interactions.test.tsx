// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ConversationThread } from '../src/features/conversations/ConversationThread';

const props = () => ({
  current_user_id: 'buyer',
  entries: [],
  key_state: { kind: 'ready' as const },
  last_read_sequence: 0,
  onRefresh: vi.fn(async () => undefined),
  onSend: vi.fn<(text: string, operationId: string) => Promise<void>>(async () => {}),
  onRetry: vi.fn<(operationId: string) => Promise<void>>(async () => {}),
  onAcknowledgeDisplayed: vi.fn(async () => undefined),
});

afterEach(() => cleanup());

describe('ConversationThread keyboard sending', () => {
  it('sends Enter through the normal encrypted send callback and prevents a newline', async () => {
    const value = props();
    render(<ConversationThread {...value} />);
    const composer = screen.getByLabelText('Message');
    fireEvent.change(composer, { target: { value: 'Hello from keyboard' } });
    const allowed = fireEvent.keyDown(composer, { key: 'Enter' });
    expect(allowed).toBe(false);
    await vi.waitFor(() => expect(value.onSend).toHaveBeenCalledWith('Hello from keyboard', expect.any(String)));
  });

  it('retries the same operation after a keyboard send failure', async () => {
    const value = props();
    value.onSend.mockRejectedValueOnce(new Error('synthetic send failure'));
    render(<ConversationThread {...value} />);
    fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'Retry this safely' } });
    fireEvent.keyDown(screen.getByLabelText('Message'), { key: 'Enter' });
    fireEvent.click(await screen.findByRole('button', { name: 'Retry' }));
    expect(value.onRetry).toHaveBeenCalledWith(value.onSend.mock.calls[0][1]);
  });

  it.each([
    ['Shift+Enter', { key: 'Enter', shiftKey: true }],
    ['IME composition Enter', { key: 'Enter', isComposing: true }],
    ['repeated Enter', { key: 'Enter', repeat: true }],
    ['another key', { key: 'a' }],
  ])('does not send for %s', (_label, key) => {
    const value = props();
    render(<ConversationThread {...value} />);
    const composer = screen.getByLabelText('Message');
    fireEvent.change(composer, { target: { value: 'Draft remains' } });
    fireEvent.keyDown(composer, key);
    expect(value.onSend).not.toHaveBeenCalled();
    expect((composer as HTMLTextAreaElement).value).toBe('Draft remains');
  });

  it('ignores a second Enter while the first send is still pending', async () => {
    let finish: (() => void) | undefined;
    const value = props();
    value.onSend.mockImplementation(() => new Promise<void>((resolve) => { finish = resolve; }));
    render(<ConversationThread {...value} />);
    const composer = screen.getByLabelText('Message');
    fireEvent.change(composer, { target: { value: 'One message' } });
    fireEvent.keyDown(composer, { key: 'Enter' });
    fireEvent.keyDown(composer, { key: 'Enter' });
    expect(value.onSend).toHaveBeenCalledTimes(1);
    finish?.();
    await vi.waitFor(() => expect(screen.queryByText('Sending…')).toBeNull());
  });

  it('scrolls the transcript to the new message after a successful send', async () => {
    const value = props();
    const sent = { entry_id: 'sent-message', sequence: 1, sender_user_id: 'buyer',
      created_at: '2026-10-29T00:00:00Z', text: 'New message at the bottom', content_deleted: false };
    function Harness() {
      const [entries, setEntries] = useState<typeof sent[]>([]);
      return <ConversationThread {...value} entries={entries} onSend={async (text, operationId) => {
        await value.onSend(text, operationId);
        setEntries([sent]);
      }} />;
    }
    render(<Harness />);
    const transcript = screen.getByRole('list');
    Object.defineProperty(transcript, 'scrollHeight', { configurable: true, value: 540 });
    fireEvent.change(screen.getByLabelText('Message'), { target: { value: sent.text } });
    fireEvent.keyDown(screen.getByLabelText('Message'), { key: 'Enter' });
    await vi.waitFor(() => expect(screen.getByText(sent.text)).toBeTruthy());
    await vi.waitFor(() => expect(screen.queryByText('Sending…')).toBeNull());
    // Scrolling runs in a React effect after the sent entry is rendered.
    await vi.waitFor(() => expect(transcript.scrollTop).toBe(540));
  });
});

it('keeps the opening unread divider stable after acknowledgement and arrivals', () => {
  const value = props();
  const entry = (sequence: number) => ({ entry_id: `message-${sequence}`, sequence, sender_user_id: 'seller',
    created_at: '2026-10-29T00:00:00.000000Z', text: `Message ${sequence}`, content_deleted: false });
  const { rerender } = render(<ConversationThread {...value} entries={[entry(1), entry(2)]}
    opening_read_sequence={1} opening_unread_count={1} />);
  const list = screen.getByText('Message 2').closest('ol');
  expect(screen.getByText('1 unread messages')).toBeTruthy();
  if (!list) throw new Error('Missing transcript');
  list.scrollTop = 37;
  rerender(<ConversationThread {...value} entries={[entry(1), entry(2), entry(3)]}
    last_read_sequence={3} opening_read_sequence={1} opening_unread_count={1} />);
  expect(screen.getByText('1 unread messages')).toBeTruthy();
  expect(list.scrollTop).toBe(37);
});

it('follows incoming messages at the bottom, preserves a reader in history, and returns without losing a draft', () => {
  const value = props();
  const entry = (sequence: number) => ({ entry_id: `live-${sequence}`, sequence, sender_user_id: 'seller',
    created_at: '2026-11-06T00:00:00Z', text: `Live ${sequence}`, content_deleted: false });
  const { rerender } = render(<ConversationThread {...value} entries={[entry(1)]} />);
  const list = screen.getByRole('list');
  Object.defineProperty(list, 'clientHeight', { configurable: true, value: 200 });
  Object.defineProperty(list, 'scrollHeight', { configurable: true, value: 500 });
  list.scrollTop = 300;
  fireEvent.scroll(list);
  Object.defineProperty(list, 'scrollHeight', { configurable: true, value: 600 });
  rerender(<ConversationThread {...value} entries={[entry(1), entry(2)]} />);
  expect(list.scrollTop).toBe(600);
  list.scrollTop = 20;
  fireEvent.scroll(list);
  rerender(<ConversationThread {...value} entries={[entry(1), entry(2), entry(3)]} viewing_history />);
  expect(list.scrollTop).toBe(20);
  fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'Unsent draft' } });
  rerender(<ConversationThread {...value} entries={[entry(2), entry(3)]} latest_view_revision={1} />);
  expect(list.scrollTop).toBe(600);
  expect((screen.getByLabelText('Message') as HTMLTextAreaElement).value).toBe('Unsent draft');
  expect(value.onAcknowledgeDisplayed).not.toHaveBeenCalled();
});
