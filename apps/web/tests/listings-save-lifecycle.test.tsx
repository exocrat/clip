// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { MemoryRouter, useLocation } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CreateListing, ListingEdit } from '../src/features/listings';
import type { ListingImageChoice } from '../src/features/listings/ListingImageSet';
import { SaleListingPreview } from '../src/features/search';

// Photo selection is outside this save-completion test. Keep the actual form,
// validation, API adapter, CSRF transport and router; no S3/network call is made.
vi.mock('../src/features/listings/ListingImageSet', () => ({
  ListingImageSet: ({ onChange, onPreviewImageChange }: { onChange: (images: ListingImageChoice[]) => void; onPreviewImageChange?: (url: string | null) => void }) => (
    <button type="button" onClick={() => { onChange([{ source: 'upload', upload_id: '30000000-0000-4000-8000-000000000001' }]); onPreviewImageChange?.('blob:synthetic-photo'); }}>Use synthetic photo</button>
  ),
}));
const id = '20000000-0000-4000-8000-000000000001';
const stamp = '2026-10-25T13:00:00.000000Z';
const record = { listing_id: id, owner_id: '11111111-2222-4333-8444-555555555555', title: 'Synthetic item', description: 'Synthetic fixture', category_code: 'books', category_label: 'Books', condition_code: 'good', condition_label: 'Good', asking_price_paise: 0, original_price_paise: null, negotiable: false, pickup_area: null, available_from: stamp, available_until: null, availability: 'available', sensitive_purchase: false, image_ids: ['30000000-0000-4000-8000-000000000001'], proof_available: null, revision: 1, selected_buyer_id: null, selected_conversation_id: null, created_at: stamp, updated_at: stamp };
function response(body: unknown) { return new Response(JSON.stringify(body), { status: 200 }); }
function Harness({ mode }: { mode: 'create' | 'edit' }) {
  const [active, setActive] = useState(true);
  const location = useLocation();
  return <><button type="button" onClick={() => setActive(false)}>Leave old actor form</button><p data-testid="current-path">{location.pathname}</p>{active && (mode === 'create' ? <CreateListing /> : <ListingEdit listingId={id} />)}</>;
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe('Listings draft preview', () => {
  it('shows the current draft through the shared sale card without publishing it', async () => {
    const fetcher = vi.fn((path: string) => {
      if (path === '/api/catalogue') return Promise.resolve(response({ categories: [{ code: 'books', label: 'Books' }], conditions: [{ code: 'good', label: 'Good' }] }));
      throw new Error(`Unexpected fixture request: ${path}`);
    });
    vi.stubGlobal('fetch', fetcher);
    render(<MemoryRouter><CreateListing renderPreview={(draft) => <SaleListingPreview draft={draft} />} /></MemoryRouter>);
    fireEvent.change(await screen.findByLabelText(/Title/), { target: { value: 'Synthetic item' } });
    fireEvent.change(screen.getByLabelText(/Description/), { target: { value: 'Synthetic fixture' } });
    fireEvent.change(screen.getByLabelText(/Item category/), { target: { value: 'books' } });
    fireEvent.change(screen.getByLabelText(/^Condition/), { target: { value: 'good' } });
    fireEvent.change(screen.getByLabelText(/Asking price/), { target: { value: '125' } });
    fireEvent.change(screen.getByLabelText(/Original price/), { target: { value: '200' } });
    fireEvent.click(screen.getByLabelText(/Price is negotiable/));
    fireEvent.click(screen.getByRole('button', { name: 'Use synthetic photo' }));
    fireEvent.click(screen.getByRole('button', { name: 'Preview listing' }));
    expect(await screen.findByRole('heading', { name: 'Synthetic item' })).toBeTruthy();
    expect(screen.getAllByText('Books').length).toBeGreaterThan(1);
    expect(screen.getByText('Condition: Good')).toBeTruthy();
    expect(screen.getByText('₹125')).toBeTruthy();
    expect(screen.getByText('Original price (Seller Provided): ₹200')).toBeTruthy();
    expect(screen.getByText('Negotiable')).toBeTruthy();
    expect(screen.getByAltText('Photo of Synthetic item').getAttribute('src')).toBe('blob:synthetic-photo');
    expect(fetcher.mock.calls.filter(([path]) => path !== '/api/catalogue')).toHaveLength(0);
  });
});

describe('Listings late save completion', () => {
  it.each([
    ['create', true], ['edit', true], ['create', false], ['edit', false],
  ] as const)('handles %s save completion with unmounted=%s', async (mode, leave) => {
    let finish: ((value: Response) => void) | undefined;
    const fetcher = vi.fn((path: string, options: RequestInit = {}) => {
      if (path === '/api/auth/csrf') return Promise.resolve(response({ csrf_token: 'c'.repeat(64) }));
      if (path === '/api/catalogue') return Promise.resolve(response({ categories: [{ code: 'books', label: 'Books' }], conditions: [{ code: 'good', label: 'Good' }] }));
      if (path.startsWith('/api/me/listings')) return Promise.resolve(response({ items: [record], page: 1, page_size: 20, has_next: false }));
      if (options.method === 'POST' || options.method === 'PUT') return new Promise<Response>((resolve) => { finish = resolve; });
      throw new Error('Unexpected fixture request');
    });
    vi.stubGlobal('fetch', fetcher);
    render(<MemoryRouter initialEntries={['/old-actor-form']}><Harness mode={mode} /></MemoryRouter>);
    const title = await screen.findByLabelText(/Title/);
    if (mode === 'create') {
      fireEvent.change(title, { target: { value: 'Synthetic item' } });
      fireEvent.change(screen.getByLabelText(/Description/), { target: { value: 'Synthetic fixture' } });
      fireEvent.change(screen.getByLabelText(/Item category/), { target: { value: 'books' } });
      fireEvent.change(screen.getByLabelText(/^Condition/), { target: { value: 'good' } });
      fireEvent.change(screen.getByLabelText(/Asking price/), { target: { value: '0' } });
      fireEvent.click(screen.getByRole('button', { name: 'Use synthetic photo' }));
    }
    fireEvent.click(screen.getByRole('button', { name: mode === 'create' ? 'Publish listing' : 'Save changes' }));
    await waitFor(() => expect(finish).toBeDefined());
    if (leave) fireEvent.click(screen.getByRole('button', { name: 'Leave old actor form' }));
    let parsed: (() => void) | undefined;
    const parsedBody = new Promise<void>((resolve) => { parsed = resolve; });
    const result = response(record);
    const readJson = result.json.bind(result);
    vi.spyOn(result, 'json').mockImplementation(async () => {
      const value = await readJson();
      parsed?.();
      return value;
    });
    await act(async () => { finish?.(result); await parsedBody; });
    await waitFor(() => expect(screen.getByTestId('current-path').textContent).toBe(leave ? '/old-actor-form' : `/listings/${id}`));
    expect(fetcher.mock.calls.filter(([, options]) => options?.method === 'POST' || options?.method === 'PUT')).toHaveLength(1);
  });
});
