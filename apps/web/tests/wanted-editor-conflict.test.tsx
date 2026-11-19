// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import { MyWantedRequests } from '../src/features/search';
import { WantedApiError } from '../src/features/search/wantedApi';

const ownerRequest = {
  request_id: '30000000-0000-4000-8000-000000000001',
  revision: 7,
  title: 'Looking for a used desk lamp',
  description: 'A working desk lamp in good condition.',
  category_code: 'books',
  category_label: 'Books',
  budget_paise: null,
  state: 'open',
};

const editWanted = vi.hoisted(() => vi.fn());
const readWanted = vi.hoisted(() => vi.fn());

vi.mock('../src/features/search/wantedApi', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../src/features/search/wantedApi')>()),
  ownWanted: vi.fn(async () => ({ items: [ownerRequest], has_next: false, page: 1, page_size: 20 })),
  editWanted,
  readWanted,
  draftMatches: vi.fn(async () => ({ items: [], has_more: false })),
}));

vi.mock('../src/features/search/discoveryApi', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../src/features/search/discoveryApi')>()),
  readDiscoveryCatalogue: vi.fn(async () => ({
    categories: [{ code: 'books', label: 'Books' }],
    conditions: [{ code: 'good', label: 'Good' }],
  })),
}));

afterEach(() => {
  cleanup();
  editWanted.mockReset();
  readWanted.mockReset();
});

const mount = () => render(<MemoryRouter><MyWantedRequests /></MemoryRouter>);

/**
 * Regression for #74: after a 409 stale_revision the editor must reload the
 * current revision so the next save targets it, instead of re-sending the stale
 * expected_revision forever. Previously both saves sent expected_revision=7.
 */
it('reloads the current revision after a 409 so the next save is not stale', async () => {
  // First save conflicts on the opened revision; the reload reports revision 8;
  // the second save then succeeds against the refreshed revision.
  editWanted
    .mockRejectedValueOnce(new WantedApiError(409))
    .mockResolvedValueOnce({ ...ownerRequest, revision: 9 });
  readWanted.mockResolvedValue({ ...ownerRequest, revision: 8 });

  const { container } = mount();
  fireEvent.click(await screen.findByRole('button', { name: 'Edit Looking for a used desk lamp' }));
  // Wait until the catalogue has populated the category option, so submit passes
  // category validation and reaches the API rather than failing locally.
  await screen.findByRole('option', { name: 'Books' });

  const save = () => {
    const form = container.querySelector('form');
    if (!form) throw new Error('editor form not rendered');
    fireEvent.submit(form);
  };
  save();
  await waitFor(() =>
    expect(screen.getByText(/we loaded the latest version/i)).toBeTruthy(),
  );
  save();
  await waitFor(() =>
    expect(screen.getByText('Your wanted request has been saved.')).toBeTruthy(),
  );

  expect(editWanted).toHaveBeenCalledTimes(2);
  expect(editWanted.mock.calls[0][1]).toMatchObject({ expected_revision: 7 });
  expect(editWanted.mock.calls[1][1]).toMatchObject({ expected_revision: 8 });
  expect(readWanted).toHaveBeenCalledTimes(1);
});
