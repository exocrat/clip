// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { IdentityProvider, useIdentity } from '../src/features/identity';
import { ListingCreatePage } from '../src/pages/ScaffoldPages';

const regular = {
  user_id: '11111111-2222-4333-8444-555555555555', account_class: 'regular',
  valid_until: '2100-01-01T00:00:00.000000Z', display_name: null,
};
function response(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), { status });
}
function setup(session: () => Response | Promise<Response>) {
  const fetcher = vi.fn((path: string) => {
    if (path === '/api/me') return Promise.resolve(session());
    if (path === '/api/catalogue') return Promise.resolve(response({ categories: [], conditions: [] }));
    throw new Error('Unexpected request');
  });
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}
function SwitchActor() {
  const { accept } = useIdentity();
  return <button type="button" onClick={() => accept({ ...regular, account_class: 'regular', user_id: 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee' })}>Switch actor</button>;
}
function view() {
  return render(<MemoryRouter><IdentityProvider><SwitchActor /><ListingCreatePage /></IdentityProvider></MemoryRouter>);
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('Real create-page composition with public Identity eligibility', () => {
  it('does not mount or fetch the seller form while eligibility is loading', () => {
    const fetcher = setup(() => new Promise<Response>(() => {}));
    view();
    expect(screen.getByRole('status').textContent).toMatch(/Checking seller eligibility/);
    expect(fetcher.mock.calls.map(([path]) => path)).toEqual(['/api/me']);
    expect(screen.queryByLabelText(/Title/)).toBeNull();
  });
  it('keeps temporary accounts out of the form and never fetches the catalogue', async () => {
    const fetcher = setup(() => response({ ...regular, account_class: 'temporary' }));
    view();
    await screen.findByText(/Temporary accounts cannot create sale listings/);
    expect(screen.queryByLabelText(/Title/)).toBeNull();
    expect(fetcher.mock.calls.map(([path]) => path)).toEqual(['/api/me']);
    expect(screen.queryByText(/Not implemented/)).toBeNull();
  });
  it.each(['anonymous', 'expired'])('asks a %s session to sign in without mounting the form', async (mode) => {
    const fetcher = setup(() => mode === 'anonymous' ? response({}, 401) : response({ ...regular, valid_until: '2000-01-01T00:00:00Z' }));
    view();
    await screen.findByRole('link', { name: 'Sign in with your IISc Microsoft account' });
    expect(fetcher.mock.calls.map(([path]) => path)).toEqual(['/api/me']);
  });
  it('fails closed during dependency failure and mounts only after a successful retry', async () => {
    let available = false;
    const fetcher = setup(() => available ? response(regular) : response({}, 503));
    view();
    await screen.findByRole('alert');
    expect(fetcher.mock.calls.map(([path]) => path)).toEqual(['/api/me']);
    available = true;
    fireEvent.click(screen.getByRole('button', { name: 'Check account again' }));
    await screen.findByLabelText(/Title/);
    expect(fetcher.mock.calls.map(([path]) => path)).toEqual(['/api/me', '/api/me', '/api/catalogue']);
  });
  it('mounts the real regular-seller form and discards drafts across actor switches', async () => {
    const fetcher = setup(() => response(regular));
    view();
    const title = await screen.findByLabelText(/Title/);
    fireEvent.change(title, { target: { value: 'Synthetic draft' } });
    fireEvent.click(screen.getByRole('button', { name: 'Switch actor' }));
    await waitFor(() => expect(fetcher.mock.calls.filter(([path]) => path === '/api/catalogue')).toHaveLength(2));
    expect((await screen.findByLabelText(/Title/)).getAttribute('value')).toBe('');
  });
});
