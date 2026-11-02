import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { checkSearchParity } from './comparison_search_parity.js';

const page = {items:[],page:1,page_size:20,has_next:false};
const cases = () => ['first', 'second', 'third'].map(q => ({request:{kind:'search',query:{q}},a:{status:200,body:structuredClone(page)},b:{status:200,body:structuredClone(page)}}));

test('reports aggregate response parity without claiming relevance or authorization', () => {
  const input=cases();
  const result=checkSearchParity(input);
  assert.equal(result.all_equal_and_valid,true);
  assert.equal(result.independent_correctness_verified,false);
  assert.equal(result.measurement_authorized,false);
  assert.equal(JSON.stringify(result).includes('first'),false);
  input[1].b.status=503;
  assert.equal(checkSearchParity(input).all_equal_and_valid,false);
});

test('refuses incomplete, duplicate and malformed case sets', () => {
  assert.throws(() => checkSearchParity(cases().slice(0,2)));
  const duplicate=cases(); duplicate[2].request.query.q='first';
  assert.throws(() => checkSearchParity(duplicate));
  const malformed=cases(); malformed[0].a.extra='private';
  assert.throws(() => checkSearchParity(malformed));
});
