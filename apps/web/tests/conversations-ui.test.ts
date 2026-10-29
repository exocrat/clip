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
  it('explains first-time peer setup without inviting acceptance or enabling send', () => {
    const html = renderThread({ key_state: { kind: 'waiting_for_peer_key' } });
    expect(html).toContain('Waiting for the other participant to set up encryption');
    expect(html).toContain('finish their account’s messaging setup before you can send');
    expect(html).toContain('role="status"');
    expect(html).toMatch(/disabled=""[^>]*>Send encrypted message/);
    expect(html).not.toContain('Encryption is not ready');
    expect(html).not.toContain('Accept new key');
  });

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
      group_unread_count: 2,
    };
    const html = renderToStaticMarkup(
      createElement(MemoryRouter, null, createElement(ConversationInbox, {
        conversations: [item],
        onRefresh: vi.fn(async () => undefined),
        onOpen: vi.fn(),
      })),
    );
    expect(html).toContain('Inbox');
    expect(html).toContain('aria-expanded="false"');
    expect(html).toContain('2 unread messages');
    expect(html).toContain('Show conversations');
    expect(html).toContain('Private messages are encrypted on your device.');
  });

  it('groups by origin with public context and no visible UUID labels', () => {
    const sharedOrigin = {
      origin_kind: 'sale_listing' as const,
      origin_id: '11111111-1111-4111-8111-111111111111',
    };
    const html = renderToStaticMarkup(
      createElement(MemoryRouter, null, createElement(ConversationInbox, {
        conversations: [
          { conversation_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', label: 'Sale listing conversation',
            role: 'seller', last_activity_at: '2026-10-23T00:00:00Z', unread_count: 1,
            group_unread_count: 1,
            counterparty_user_id: '22222222-2222-4222-8222-222222222222', current_offer: { amount_paise: 125000, status: 'submitted' }, ...sharedOrigin },
          { conversation_id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', label: 'Sale listing conversation',
            role: 'seller', last_activity_at: '2026-10-22T00:00:00Z', unread_count: 0,
            group_unread_count: 1,
            counterparty_user_id: '33333333-3333-4333-8333-333333333333', current_offer: null, ...sharedOrigin },
          { conversation_id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc', label: 'Wanted request conversation',
            role: 'request author', last_activity_at: '2026-10-21T00:00:00Z', unread_count: 0,
            origin_kind: 'wanted_request', origin_id: '44444444-4444-4444-8444-444444444444' },
        ],
        filters: { view: 'all', sort: 'last_activity_desc' },
        onFiltersChange: vi.fn(),
        onRefresh: vi.fn(async () => undefined),
        onOpen: vi.fn(),
        renderOriginContext: (kind) => createElement('span', null, kind === 'sale_listing' ? 'Synthetic bicycle · ₹1,250' : 'Synthetic Wanted request · Budget not stated'),
      })),
    );
    expect(html).toContain('Sale listing');
    expect(html).toContain('2 conversations');
    expect(html).toContain('Synthetic bicycle · ₹1,250');
    expect(html).toContain('Synthetic Wanted request · Budget not stated');
    expect(html).not.toContain('Partner 22222222');
    expect(html).not.toContain('11111111…1111');
    expect(html).toContain('Show conversations');
    expect(html).toContain('Most recent activity first.');
    expect(html).not.toContain('Partner · 22222222-2222-4222-8222-222222222222');
  });

  it('omits an empty Sort & Filter disclosure and obsolete selectors', () => {
    const html = renderToStaticMarkup(
      createElement(ConversationInbox, {
        conversations: [],
        filters: { view: 'all', sort: 'last_activity_desc' },
        onFiltersChange: vi.fn(),
        onRefresh: vi.fn(async () => undefined),
        onOpen: vi.fn(),
      }),
    );
    expect(html).not.toContain('<details class="conversation-inbox__sort-filter">');
    expect(html).not.toContain('Sort &amp; Filter');
    expect(html).not.toContain('Participation');
    expect(html).not.toContain('Conversation partner');
    expect(html).not.toContain('Listing or request');
    expect(html).not.toContain('Minimum offer');
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
