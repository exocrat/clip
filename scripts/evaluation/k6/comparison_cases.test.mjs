import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { readFileSync } from 'node:fs';
import { approvedApiTarget, comparisonPath } from './comparison_cases.js';

test('approved HTTPS targets work without a browser URL global and reject unsafe origins', () => {
  const original = globalThis.URL;
  try {
    globalThis.URL = undefined;
    assert.equal(approvedApiTarget('https://clip-iisc.site/api', 'https://clip-iisc.site'), 'https://clip-iisc.site/api');
    assert.equal(approvedApiTarget('https://clip-iisc.site:443/api', 'https://clip-iisc.site:443'), 'https://clip-iisc.site:443/api');
    for (const origin of ['http://clip-iisc.site', 'https://user@clip-iisc.site', 'https://clip-iisc.site/path', 'https://clip-iisc.site?x', 'https://clip-iisc.site#x', 'https://clip-iisc.site:8443', 'https://clip-iisc.site\\@other.site', 'https://-bad.site', 'https://bad..site', 'https://clip-iisc.site\n']) {
      assert.throws(() => approvedApiTarget(`${origin}/api`, origin));
    }
    assert.throws(() => approvedApiTarget('https://other.site/api', 'https://clip-iisc.site'));
  } finally { globalThis.URL = original; }
});

test('comparison requests use generated public GET operations and query names', () => {
  const spec = JSON.parse(readFileSync(new URL('../../../contracts/generated/openapi.json', import.meta.url)));
  assert.equal(spec.paths['/listings'].get.operationId, 'listings_query_available');
  assert.equal(spec.paths['/listings/{listing_id}'].get.operationId, 'listings_read_detail');
  const names = new Set(spec.paths['/listings'].get.parameters.map(p => p.name));
  for (const name of ['q', 'search_mode', 'category_code', 'page']) assert.ok(names.has(name));
  assert.equal(comparisonPath({kind:'browse', query:{category_code:['books','electronics'], page:2}}), '/listings?page=2&category_code=books&category_code=electronics');
  assert.equal(comparisonPath({kind:'search', query:{q:'study desk', search_mode:'hybrid'}}), '/listings?q=study%20desk&search_mode=hybrid');
  assert.equal(comparisonPath({kind:'detail', listing_id:'01b4fbd6-4c3c-44da-a578-6284033a869c'}), '/listings/01b4fbd6-4c3c-44da-a578-6284033a869c');
});

test('rejects invented routes, malformed IDs and non-Hybrid search', () => {
  for (const item of [{kind:'detail',listing_id:'../../me'}, {kind:'search',query:{q:'x',search_mode:'keyword'}}, {kind:'search',query:{q:'x'}}, {kind:'browse',query:{q:'x'}}, {kind:'browse',query:{actor_id:'x'}}]) assert.throws(() => comparisonPath(item));
});
