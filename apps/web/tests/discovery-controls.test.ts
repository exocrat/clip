import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { SaleDiscovery } from '../src/features/search/SaleDiscovery';

/** Static accessibility/URL rendering checks; effects and human browser behavior
 * are verified separately, rather than claiming server rendering runs requests. */
const render = (url: string) => renderToStaticMarkup(createElement(MemoryRouter,
  { initialEntries: [url] }, createElement(SaleDiscovery)));

describe('mode and relevance controls', () => {
  it('keeps Newest/Relevance controls without offering a search mode selector', () => {
    const html = render('/');
    expect(html).not.toContain('id="discovery-mode"');
    expect(html).not.toContain('Search mode');
    expect(html).not.toContain('Use Keyword');
    expect(html).toContain('<option value="created_desc" selected="">Newest first</option>');
    expect(html).toContain('<option value="relevance" disabled="">Relevance</option>');
    expect(html).toContain('aria-describedby="discovery-sort-help"');
  });
  it.each(['keyword', 'hybrid'])('restores a %s/relevance bookmark without a mode selector', (mode) => {
    const html = render(`/?q=vehicle&search_mode=${mode}&sort=relevance`);
    expect(html).not.toContain('id="discovery-mode"');
    expect(html).toContain('<option value="relevance" selected="">Relevance</option>');
    expect(html).toContain('Orders matching listings.');
    expect(html).not.toContain('Hybrid takes effect when search text is entered.');
  });
});
