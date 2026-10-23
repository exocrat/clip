import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter, Route, Routes } from 'react-router';
import { describe, expect, it } from 'vitest';
import { ConversationDemoPage } from '../src/pages/ConversationDemo';

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
    expect(html).toContain('Demo bicycle listing · Sample buyer');
    expect(html).toContain('2 unread');
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
