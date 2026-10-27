import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter, Route, Routes } from 'react-router';
import { describe, expect, it } from 'vitest';
import { ConversationDemoPage } from '../src/pages/ConversationDemo';
import { createConversationDemoState, DEMO_CONVERSATION_ID } from '../src/pages/conversationDemoState';

function renderDemo(path: string, page: 'inbox' | 'thread', conversationId?: string) {
  return renderToStaticMarkup(
    createElement(
      MemoryRouter,
      { initialEntries: [path] },
      createElement(
        Routes,
        null,
        createElement(Route, {
          path: '/my/conversations/*',
          element: createElement(ConversationDemoPage, { page, conversationId }),
        }),
      ),
    ),
  );
}

describe('loopback conversation demo pages', () => {
  it('shows an explicitly labeled synthetic inbox without claiming service integration', () => {
    const html = renderDemo('/my/conversations?demo=conversations', 'inbox');
    expect(html).toContain('Development demo · synthetic data only');
    expect(html).toContain('No account, API, or encryption service is connected.');
    expect(html).toContain('Unread badges update locally as messages are displayed and also reset on reload.');
    expect(html).toContain('Demo bicycle listing · Sample buyer');
    expect(html).toContain('2 unread');
  });

  it('updates demo unread counts only through visible-sequence acknowledgements', () => {
    const state = createConversationDemoState();
    expect(state.getInboxItems().find((item) => item.conversation_id === DEMO_CONVERSATION_ID)?.unread_count).toBe(2);
    expect(state.markDisplayed(DEMO_CONVERSATION_ID, 2)).toBe(true);
    expect(state.getInboxItems().find((item) => item.conversation_id === DEMO_CONVERSATION_ID)?.unread_count).toBe(1);
    expect(state.markDisplayed(DEMO_CONVERSATION_ID, 1)).toBe(false);
    expect(state.markDisplayed(DEMO_CONVERSATION_ID, 99)).toBe(false);
    expect(state.getInboxItems().find((item) => item.conversation_id === DEMO_CONVERSATION_ID)?.unread_count).toBe(1);
    expect(state.markDisplayed(DEMO_CONVERSATION_ID, 3)).toBe(true);
    expect(state.getInboxItems().find((item) => item.conversation_id === DEMO_CONVERSATION_ID)?.unread_count).toBe(0);
  });

  it('keeps new demo messages local, advances ordering, and starts clean in a fresh state', () => {
    const state = createConversationDemoState();
    expect(state.addMessage(DEMO_CONVERSATION_ID, 'Synthetic follow-up', '2026-10-24T12:00:00Z')).toBe(true);
    expect(state.getEntries(DEMO_CONVERSATION_ID).at(-1)).toMatchObject({
      sequence: 4, sender_user_id: 'demo-current-user', text: 'Synthetic follow-up',
    });
    expect(state.getInboxItems().find((item) => item.conversation_id === DEMO_CONVERSATION_ID)?.unread_count).toBe(2);
    const freshPageLoad = createConversationDemoState();
    expect(freshPageLoad.getEntries(DEMO_CONVERSATION_ID)).toHaveLength(3);
    expect(freshPageLoad.getInboxItems().find((item) => item.conversation_id === DEMO_CONVERSATION_ID)?.unread_count).toBe(2);
  });

  it('shows the thread with truthful local-only encryption and send copy', () => {
    const html = renderDemo(
      '/my/conversations/demo-bicycle?demo=conversations',
      'thread',
      'demo-bicycle',
    );
    expect(html).toContain('Local demo only: messages are not encrypted or sent to a service.');
    expect(html).toContain('Add demo message');
    expect(html).toContain('Hi! Is this demo bicycle still available?');
  });
});
