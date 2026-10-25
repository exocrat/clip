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
  it('defaults to Keyword/Newest, explains blank behavior and keeps mode outside draft form', () => {
    const html = render('/');
    expect(html).toContain('<option value="keyword" selected="">Keyword</option>');
    expect(html).toContain('<option value="created_desc" selected="">Newest first</option>');
    expect(html).toContain('<option value="relevance" disabled="">Relevance</option>');
    expect(html).toContain('Matches words and known item terms, with limited typo tolerance.');
    expect(html).toContain('Hybrid takes effect when search text is entered.');
    expect(html.indexOf('id="discovery-mode"')).toBeLessThan(html.indexOf('<form'));
    expect(html).toContain('aria-describedby="discovery-mode-help"');
    expect(html).toContain('aria-describedby="discovery-sort-help"');
  });
  it.each(['keyword', 'hybrid'])('restores a %s/relevance bookmark with visible help and enabled relevance', (mode) => {
    const html = render(`/?q=vehicle&search_mode=${mode}&sort=relevance`);
    expect(html).toContain(`<option value="${mode}" selected="">`);
    expect(html).toContain('<option value="relevance" selected="">Relevance</option>');
    expect(html).toContain(mode === 'hybrid' ? 'Adds related meanings to keyword matches.' : 'Matches words and known item terms, with limited typo tolerance.');
    expect(html).toContain('Orders matches using the selected search mode.');
    expect(html).not.toContain('Hybrid takes effect when search text is entered.');
  });
});
