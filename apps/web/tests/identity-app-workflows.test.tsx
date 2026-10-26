// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Link, MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { IdentityProvider, IdentitySessionControl, SignIn } from '../src/features/identity';
import { ListingCreatePage, MyListingsPage } from '../src/pages/ScaffoldPages';

const temporary = {
  user_id: '11111111-2222-4333-8444-555555555555',
  account_class: 'temporary',
  valid_until: '2100-01-01T00:00:00.000000Z',
  display_name: null,
};
const regular = { ...temporary, user_id: 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee', account_class: 'regular' };
const challenge = {
  challenge_id: 'bbbbbbbb-cccc-4ddd-8eee-ffffffffffff',
  expires_at: '2100-01-01T00:00:00.000000Z',
};

function response(value: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(value), { status });
}

function Navigation() {
  return (
    <nav aria-label="Workflow test navigation">
      <Link to="/sign-in">Sign in</Link>
      <Link to="/listings/new">New listing</Link>
      <Link to="/my/listings">My listings</Link>
    </nav>
  );
}

function app() {
  return render(
    <MemoryRouter initialEntries={['/sign-in']}>
      <IdentityProvider>
        <IdentitySessionControl />
        <Navigation />
        <Routes>
          <Route path="/sign-in" element={<SignIn />} />
          <Route path="/listings/new" element={<ListingCreatePage />} />
          <Route path="/my/listings" element={<MyListingsPage />} />
        </Routes>
      </IdentityProvider>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('app-level identity and seller workflows with synthetic HTTP fixtures', () => {
  it('registers a temporary account, logs back in, blocks sale listings, and keeps Wanted Requests available', async () => {
    let active: typeof temporary | null = null;
    const requests: { path: string; init: RequestInit }[] = [];
    const fetcher = vi.fn((path: string, init: RequestInit) => {
      requests.push({ path, init });
      if (path === '/api/me') return Promise.resolve(active ? response(active) : response({}, 401));
      if (path === '/api/auth/csrf') return Promise.resolve(response({ csrf_token: 'c'.repeat(64) }));
      if (path === '/api/auth/session' && init.method === 'DELETE') {
        active = null;
        return Promise.resolve(response(null, 204));
      }
      if (path === '/api/auth/temporary/registration-challenges') return Promise.resolve(response(challenge, 202));
      if (path === '/api/auth/temporary/accounts') {
        active = temporary;
        return Promise.resolve(response(temporary, 201));
      }
      if (path === '/api/auth/temporary/sessions') {
        active = temporary;
        return Promise.resolve(response(temporary));
      }
      if (path === '/api/me/wanted-requests?page=1&page_size=20') {
        return Promise.resolve(response({ items: [], page: 1, page_size: 20, has_next: false }));
      }
      if (path === '/api/me/listings?page=1&page_size=20') {
        return Promise.resolve(response({ items: [], page: 1, page_size: 20, has_next: false }));
      }
      if (path === '/api/catalogue') throw new Error('Temporary account reached seller form data');
      throw new Error(`Unexpected synthetic request: ${path}`);
    });
    vi.stubGlobal('fetch', fetcher);

    const user = userEvent.setup();
    app();
    await screen.findByRole('button', { name: 'Create temporary account' });
    await user.click(screen.getByRole('button', { name: 'Create temporary account' }));
    await user.type(screen.getByLabelText('Email address'), 'synthetic@example.invalid');
    await user.click(screen.getByRole('button', { name: 'Send verification code' }));
    await screen.findByRole('button', { name: 'Verify and create account' });
    await user.type(screen.getByLabelText('Verification code'), '123456');
    await user.type(screen.getByLabelText('Password'), 'syntheticPass');
    await user.click(screen.getByRole('button', { name: 'Verify and create account' }));
    await screen.findByRole('heading', { name: 'You’re signed in' });

    await user.click(screen.getByRole('button', { name: 'Sign out' }));
    await screen.findByRole('heading', { name: 'Welcome back' });
    await user.type(screen.getByLabelText('Email address'), 'synthetic@example.invalid');
    await user.type(screen.getByLabelText('Password'), 'syntheticPass');
    await user.click(screen.getByRole('button', { name: /^Sign in$/ }));
    await screen.findByRole('heading', { name: 'You’re signed in' });

    await user.click(screen.getByRole('link', { name: 'New listing' }));
    await screen.findByText(/Temporary accounts cannot create sale listings/);
    expect(screen.queryByLabelText(/Title/)).toBeNull();
    expect(requests.some(({ path }) => path === '/api/catalogue')).toBe(false);

    await user.click(screen.getByRole('link', { name: 'My listings' }));
    await screen.findByRole('button', { name: 'Sale Listings' });
    await user.click(screen.getByRole('button', { name: 'Wanted Requests' }));
    expect(await screen.findByRole('button', { name: 'Create wanted request' })).toBeTruthy();

    const registration = requests.find(({ path }) => path.endsWith('/registration-challenges'));
    expect(registration?.init.body).toContain('synthetic@example.invalid');
    expect(requests.filter(({ path }) => path.endsWith('/sessions'))).toHaveLength(1);
    expect(requests.some(({ path, init }) => path === '/api/auth/session' && init.method === 'DELETE')).toBe(true);
    expect(requests.every(({ path }) => path.startsWith('/api/'))).toBe(true);
  });

  it('lets a synthetic IISc session reach the regular seller form without external sign-in', async () => {
    const fetcher = vi.fn((path: string) => {
      if (path === '/api/me') return Promise.resolve(response(regular));
      if (path === '/api/catalogue') return Promise.resolve(response({
        categories: [{ code: 'books', label: 'Books' }],
        conditions: [{ code: 'good', label: 'Good' }],
      }));
      throw new Error(`Unexpected synthetic request: ${path}`);
    });
    vi.stubGlobal('fetch', fetcher);

    app();
    await screen.findByRole('link', { name: 'New listing' });
    await userEvent.setup().click(screen.getByRole('link', { name: 'New listing' }));
    await screen.findByRole('button', { name: 'Publish listing' });
    expect(screen.getByLabelText(/Title/)).toBeTruthy();
    expect(fetcher.mock.calls.map(([path]) => path)).toEqual(['/api/me', '/api/catalogue']);
  });
});
