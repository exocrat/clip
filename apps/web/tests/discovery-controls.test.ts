import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { Link, MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { SaleDiscovery } from '../src/features/search/SaleDiscovery';
import { SaleListingCard } from '../src/features/search/SaleListingCard';
import type { ListingSummary } from '../src/features/search/discoveryApi';

/** Static accessibility/URL rendering checks; effects and human browser behavior
 * are verified separately, rather than claiming server rendering runs requests. */
const render = (url: string) => renderToStaticMarkup(createElement(MemoryRouter,
  { initialEntries: [url] }, createElement(SaleDiscovery)));
const listing: ListingSummary = { listing_id: '20000000-0000-4000-8000-000000000001', title: 'Synthetic item',
  description: 'Synthetic fixture', category_code: 'books', category_label: 'Books', condition_code: 'good',
  condition_label: 'Good', asking_price_paise: 100, original_price_paise: null, negotiable: true, pickup_area: null,
  available_from: '2026-01-01T00:00:00.000000Z', available_until: null, availability: 'available',
  sensitive_purchase: false, image_ids: [] };

describe('mode and relevance controls', () => {
  it('keeps browse sorting without exposing negotiability or a Best Match choice when no search is active', () => {
    const html = render('/');
    expect(html).not.toContain('id="discovery-mode"');
    expect(html).not.toContain('Search mode');
    expect(html).not.toContain('Use Keyword');
    expect(html).not.toContain('id="discovery-negotiable"');
    expect(html).toContain('<option value="created_desc" selected="">Newest first</option>');
    expect(html).not.toContain('<option value="relevance"');
    expect(html).not.toContain('>Best Match</option>');
    expect(html).not.toContain('discovery-sort-help');
  });
  it.each(['keyword', 'hybrid'])('restores a %s/relevance bookmark without a mode selector', (mode) => {
    const html = render(`/?q=vehicle&search_mode=${mode}&sort=relevance`);
    expect(html).not.toContain('id="discovery-mode"');
    expect(html).toContain('<option value="relevance" selected="">Best Match</option>');
    expect(html).not.toContain('Text searches default to Best Match');
    expect(html).not.toContain('Hybrid takes effect when search text is entered.');
  });
  it('shows the complete negotiability state as a card badge', () => {
    const html = renderToStaticMarkup(createElement(MemoryRouter, null,
      createElement(SaleListingCard, { listing })));
    expect(html).toContain('<span class="discovery-negotiability">Negotiable</span>');
    expect(html).toContain('<strong>Condition:</strong> Good');
  });
  it('omits the original-price row when a listing has no original price', () => {
    const html = renderToStaticMarkup(createElement(MemoryRouter, null,
      createElement(SaleListingCard, { listing })));
    expect(html).not.toContain('discovery-card__original-price');
  });
  it('accepts the eligible seller creation action above the search controls', () => {
    const html = renderToStaticMarkup(createElement(MemoryRouter, null,
      createElement(SaleDiscovery, { createListingAction: createElement(Link, { to: '/listings/new', className: 'ui-button ui-button--primary' }, 'New Listing') })));
    expect(html.indexOf('New Listing')).toBeLessThan(html.indexOf('Search listings'));
    expect(html).toContain('href="/listings/new"');
  });
});
