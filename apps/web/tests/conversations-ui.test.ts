import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import {
  ConversationInbox,
  ConversationThread,
  ConversationInboxPage,
  ConversationDetailPage,
  KEY_REGISTRATION_WARNING,
  PEER_KEY_CHANGE_WARNING,
  type ConversationDisplayEntry,
  type ConversationInboxItem,
} from '../src/features/conversations';

const entry: ConversationDisplayEntry = {
  entry_id: 'entry-1',
  sequence: 1,
  sender_user_id: 'alice',
  created_at: '2026-10-23T00:00:00Z',
  text: '<script>alert(1)</script>',
  content_deleted: false,
};

function renderThread(overrides: Partial<Parameters<typeof ConversationThread>[0]> = {}) {
  return renderToStaticMarkup(
    createElement(ConversationThread, {
      current_user_id: 'alice',
      entries: [entry],
      key_state: { kind: 'ready' },
      last_read_sequence: 0,
      onRefresh: vi.fn(async () => undefined),
      onSend: vi.fn(async () => undefined),
      onRetry: vi.fn(async () => undefined),
      onAcknowledgeDisplayed: vi.fn(async () => undefined),
      ...overrides,
    }),
  );
}

describe('ConversationThread UI', () => {
  it('renders message text as text, never as markup', () => {
    const html = renderThread();
    expect(html).toContain('&lt;script&gt;alert(1)&lt;/script&gt;');
    expect(html).not.toContain('<script>');
    expect(html).toContain('Send encrypted message');
  });

  it('shows recipient decryption failure on the original message without presenting it as an unsent message', () => {
    const html = renderThread({ entries: [{ ...entry, delivery_notice: 'recipient_unable_to_decrypt' }] });
    expect(html).toContain('The recipient couldn’t decrypt this message. You can send it again as a new message.');
    expect(html).not.toContain('Message not sent.');
    expect(html).not.toContain('Retrying…');
  });

  it('identifies the local demo as unencrypted and local-only', () => {
    const html = renderThread({ presentationMode: 'local-demo' });
    expect(html).toContain('messages are not encrypted or sent to a service');
    expect(html).toContain('Add demo message');
    expect(html).not.toContain('Send encrypted message');
  });

  it('shows the account-directory warning and provides no ignore/continue action on key change', () => {
    const html = renderThread({
      key_state: { kind: 'key_change', participant_label: 'The other participant' },
    });
    expect(html).toContain('Encryption key changed');
    expect(html).toContain(PEER_KEY_CHANGE_WARNING);
    expect(html).toContain('Accept new key');
    expect(html).not.toContain('Ignore');
    expect(html).not.toContain('Continue anyway');
    expect(html).toContain('disabled="" id="conversation-message-draft"');
  });

  it('requires explicit history-loss acknowledgement before enabling first key creation', () => {
    const html = renderThread({
      entries: [],
      key_state: { kind: 'registration_acknowledgement_required' },
    });
    expect(html).toContain(KEY_REGISTRATION_WARNING);
    expect(html).toContain('I understand that lost browser key data cannot be restored.');
    expect(html).toContain('Create encryption key');
    expect(html).toContain('disabled="" type="button">Create encryption key');
  });

  it('explains lost local key state without offering server recovery', () => {
    const html = renderThread({
      entries: [],
      key_state: { kind: 'key_state_lost' },
    });
    expect(html).toContain('This browser has lost its encryption key.');
    expect(html).toContain('CLIP cannot restore it');
    expect(html).not.toContain('Recover key');
    expect(html).toContain('disabled="" id="conversation-message-draft"');
  });
});

describe('ConversationInbox UI', () => {
  it('renders accessible participant-scoped rows and unread counts', () => {
    const item: ConversationInboxItem = {
      conversation_id: 'conversation-1',
      label: 'A bicycle listing',
      role: 'buyer',
      last_activity_at: '2026-10-23T00:00:00Z',
      unread_count: 2,
    };
    const html = renderToStaticMarkup(
      createElement(ConversationInbox, {
        conversations: [item],
        onRefresh: vi.fn(async () => undefined),
        onOpen: vi.fn(),
      }),
    );
    expect(html).toContain('Your conversations');
    expect(html).toContain('aria-label="Open A bicycle listing"');
    expect(html).toContain('>2 unread</span>');
    expect(html).toContain('Private messages are encrypted on your device.');
  });
});

describe('Conversation route composition', () => {
  it('keeps inbox and thread unavailable until Identity supplies an authenticated runtime', () => {
    const inbox = renderToStaticMarkup(createElement(MemoryRouter, null, createElement(ConversationInboxPage)));
    const thread = renderToStaticMarkup(createElement(ConversationDetailPage, { conversationId: 'sample-id' }));
    expect(inbox).toContain('Sign in to load your conversations');
    expect(thread).toContain('Sign in to view this conversation');
    expect(inbox).not.toContain('sample');
    expect(thread).not.toContain('Send encrypted message');
  });
});
