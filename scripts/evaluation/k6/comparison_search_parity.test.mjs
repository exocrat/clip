import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { checkSearchParity } from './comparison_search_parity.js';

const page = {items:[],page:1,page_size:20,has_next:false};
const corpus = () => ({cases:['direct_word','related_word','meaning_based'].map((query_class,i) => ({case_id:`case-${i}`,request:{kind:'search',query:{q:`query-${i}`,search_mode:'hybrid'}},relevance_reference:{query_class}}))});
const cases = source => source.cases.map(({case_id,request}) => ({case_id,request:structuredClone(request),a:{status:200,body:structuredClone(page)},b:{status:200,body:structuredClone(page)}}));

test('reports aggregate response parity without claiming relevance or authorization', () => {
  const source=corpus(), input=cases(source);
  const result=checkSearchParity(input,source);
  assert.equal(result.all_equal_and_valid,true);
  assert.equal(result.independent_correctness_verified,false);
  assert.equal(result.measurement_authorized,false);
  assert.equal(JSON.stringify(result).includes('query-0'),false);
  input[1].b.status=503;
  assert.equal(checkSearchParity(input,source).all_equal_and_valid,false);
});

test('refuses incomplete, duplicate and malformed case sets', () => {
  const source=corpus();
  assert.throws(() => checkSearchParity(cases(source).slice(0,2),source));
  const duplicate=cases(source); duplicate[2].case_id='case-0';
  assert.throws(() => checkSearchParity(duplicate,source));
  const changed=cases(source); changed[0].request.query.q='different';
  assert.throws(() => checkSearchParity(changed,source));
  const malformed=cases(source); malformed[0].a.extra='private';
  assert.throws(() => checkSearchParity(malformed,source));
  const wrongClasses=corpus(); wrongClasses.cases[2].relevance_reference.query_class='direct_word';
  assert.throws(() => checkSearchParity(cases(wrongClasses),wrongClasses));
});
