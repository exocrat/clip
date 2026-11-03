import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { spawnSync } from 'node:child_process';
import { closeSync, mkdtempSync, openSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
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

test('offline command returns aggregate only and fails for mismatched or unsafe input', () => {
  const source=corpus(), input=cases(source);
  const run = value => {
    const directory=mkdtempSync(join(tmpdir(),'parity-input-'));
    try {
      const path=join(directory,'input.json'); writeFileSync(path,value);
      const fd=openSync(path,'r');
      try { return spawnSync(process.execPath, ['scripts/evaluation/k6/comparison_search_parity_cli.mjs'], {stdio:[fd,'pipe','pipe'],encoding:'utf8',timeout:10000}); }
      finally { closeSync(fd); }
    } finally { rmSync(directory,{recursive:true,force:true}); }
  };
  const match=run(JSON.stringify({corpus:source,cases:input}));
  assert.equal(match.status,0);
  assert.ok(match.stdout, JSON.stringify(match));
  assert.equal(JSON.parse(match.stdout).measurement_authorized,false);
  assert.equal(match.stdout.includes('query-0'),false);
  input[0].b.status=500;
  assert.equal(run(JSON.stringify({corpus:source,cases:input})).status,2);
  const invalid=run('{"secret":"synthetic-private"}');
  assert.equal(invalid.status,2);
  assert.equal(invalid.stderr.includes('synthetic-private'),false);
  assert.equal(invalid.stdout,'');
  assert.equal(run('x'.repeat(5_000_001)).status,2);
});
