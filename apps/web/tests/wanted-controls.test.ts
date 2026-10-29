import { createElement, type ComponentType } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import {
  MyWantedRequests,
  SavedListings,
  WantedBrowse,
  WantedDetail,
  WantedContactAction,
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
  it('places possible sale matches before the Wanted publish action', () => {
    const createWanted = MyWantedRequests as ComponentType<{ startCreating?: boolean }>;
    const html = render(createElement(createWanted, { startCreating: true }));
    expect(html.indexOf('Enter a title to see possible sale matches.')).toBeLessThan(html.indexOf('Publish request'));
    expect(html).toContain('Enter a title to see possible sale matches.');
  });
  it('shows public browse loading without inventing records or exposing author contact information', () => {
    const html = render(createElement(WantedBrowse));
    expect(html).toContain('Loading wanted requests…');
    expect(html).toContain('New Wanted Request');
    expect(html).toContain('/my/listings?view=wanted&amp;create=wanted');
    expect(html).not.toContain('Contact requester');
    expect(html).not.toContain('@');
  });
  it('renders requester contact on an eligible Wanted card action', () => {
    const html = render(createElement(WantedContactAction, {
      requestId: '20000000-0000-4000-8000-000000000001',
      compact: true,
      session: { data: {
        user_id: '20000000-0000-4000-8000-000000000002',
        account_class: 'regular',
        valid_until: '2100-01-01T00:00:00.000000Z',
      } },
    }));
    expect(html).toContain('Contact requester');
    expect(html).not.toContain('disabled');
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
