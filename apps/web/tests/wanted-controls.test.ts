import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import {
  MyWantedRequests,
  SavedListings,
  WantedBrowse,
  WantedDetail,
  SaveListingAction,
} from '../src/features/search';
const render = (component: ReturnType<typeof createElement>) =>
  renderToStaticMarkup(createElement(MemoryRouter, {}, component));
/** SSR checks initial safe controls only; interactive/viewport verification remains a human browser gate. */
describe('search composition initial safety', () => {
  it('keeps private owner and saved lists behind fresh loading state', () => {
    expect(render(createElement(MyWantedRequests))).toContain('Create wanted request');
    expect(render(createElement(SavedListings))).toContain('Loading…');
  });
  it('shows public browse loading without inventing records or author contact information', () => {
    const html = render(createElement(WantedBrowse));
    expect(html).toContain('Loading…');
    expect(html).not.toContain('Contact requester');
  });
  it('rejects malformed routes without showing response/save actions', () => {
    expect(render(createElement(WantedDetail, { requestId: 'bad' }))).toContain('link is invalid');
    expect(render(createElement(SaveListingAction, { listingId: 'bad' }))).toBe('');
  });
  it('does not enable contact before actual detail and eligibility arrive', () => {
    const html = render(createElement(WantedDetail, { requestId: '20000000-0000-4000-8000-000000000001' }));
    expect(html).toContain('Loading…');
    expect(html).not.toContain('Contact requester');
  });
});
