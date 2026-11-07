// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import { createElement } from 'react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

const identityState = vi.hoisted(() => ({ value: { status: 'anonymous', user: null } as {
  status: 'anonymous' | 'ready';
  user: null | { account_class: 'regular' | 'temporary'; valid_until: string; display_name: string | null };
} }));

vi.mock('../src/features/identity', () => ({
  useIdentity: () => identityState.value,
  HandleSetup: ({ children }: { children?: React.ReactNode }) => createElement('div', null, children),
  IdentitySessionControl: () => createElement('button', { type: 'button' }, 'Sign out'),
}));
vi.mock('../src/features/conversations', () => ({
  ConversationUnreadBadge: () => null,
  useConversationUnreadCount: () => null,
  ConversationKeySetup: ({ children }: { children?: React.ReactNode }) => createElement('div', null, children),
}));

import { AppShell } from '../src/app/AppShell';

afterEach(() => cleanup());

function renderShell() {
  return render(<MemoryRouter><AppShell /></MemoryRouter>);
}

describe('marketplace shell navigation', () => {
  it('shows only product routes and Sign in when signed out', () => {
    identityState.value = { status: 'anonymous', user: null };
    renderShell();
    const nav = screen.getByRole('navigation', { name: 'Marketplace' });
    for (const label of ['Sign in', 'Discover', 'My Wanted Requests', 'My Listings', 'Saved', 'Conversations', 'Account']) {
      expect(nav.textContent).toContain(label);
    }
    expect(nav.textContent).not.toContain('Auth callback');
    expect(nav.textContent).not.toContain('Listing detail');
    expect(nav.textContent).not.toContain('Conversation</');
    expect(screen.queryByRole('button', { name: 'Sign out' })).toBeNull();
  });

  it('places the regular seller account action in the top row and omits Sign in', () => {
    identityState.value = { status: 'ready', user: {
      account_class: 'regular', valid_until: '2100-01-01T00:00:00.000000Z', display_name: 'Seller',
    } };
    renderShell();
    const top = screen.getByRole('link', { name: 'CLIP' }).parentElement;
    expect(top?.className).toBe('app-shell__top');
    expect(top?.querySelector('.app-shell__account')?.textContent).toContain('Sign out');
    expect(screen.queryByRole('link', { name: 'Sign in' })).toBeNull();
    expect(screen.getByRole('navigation', { name: 'Marketplace' }).textContent).toContain('New Listing');
  });

  it('hides the sale-create route from temporary accounts but keeps Wanted creation', () => {
    identityState.value = { status: 'ready', user: {
      account_class: 'temporary', valid_until: '2100-01-01T00:00:00.000000Z', display_name: null,
    } };
    renderShell();
    const nav = screen.getByRole('navigation', { name: 'Marketplace' });
    expect(nav.textContent).not.toContain('New Listing');
    expect(nav.textContent).toContain('My Wanted Requests');
  });
});
