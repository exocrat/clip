import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { spawnSync } from 'node:child_process';
import { closeSync, mkdtempSync, openSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { checkAllParity } from './comparison_all_parity.js';

const id='01b4fbd6-4c3c-44da-a578-6284033a869c';
const row={listing_id:id,title:'Synthetic bicycle',description:'Synthetic',category_code:'bicycles',category_label:'Bicycles',condition_code:'good',condition_label:'Good',asking_price_paise:10000,original_price_paise:null,negotiable:true,pickup_area:null,available_from:'2026-01-01T00:00:00.000000Z',available_until:null,availability:'available',sensitive_purchase:false,image_ids:[id]};
const page={items:[row],page:1,page_size:20,has_next:false};
const corpus=()=>({cases:[
  ...Array.from({length:5},(_,i)=>({case_id:`browse-${i}`,request:{kind:'browse',query:{page:1}}})),
  ...['direct_word','related_word','meaning_based'].map((query_class,i)=>({case_id:`search-${i}`,request:{kind:'search',query:{q:`q-${i}`}},relevance_reference:{query_class}})),
  ...Array.from({length:2},(_,i)=>({case_id:`detail-${i}`,request:{kind:'detail',listing_id:id}})),
]});
const responses=source=>source.cases.map(({case_id,request})=>({case_id,request:structuredClone(request),a:{status:200,body:structuredClone(request.kind==='detail'?{...row,proof_available:null}:page)},b:{status:200,body:structuredClone(request.kind==='detail'?{...row,proof_available:null}:page)}}));

test('compares all ten without claiming authorization or independent correctness',()=>{
  const source=corpus(), cases=responses(source);
  const result=checkAllParity(cases,source);
  assert.equal(result.all_equal_and_valid,true);
  assert.equal(result.independent_correctness_verified,false);
  assert.equal(result.measurement_authorized,false);
  assert.equal(JSON.stringify(result).includes('Synthetic'),false);
  for (const index of [0,5,8]) {
    const changed=structuredClone(cases); changed[index].b.body.items ? changed[index].b.body.items[0].title='Changed' : changed[index].b.body.title='Changed';
    assert.equal(checkAllParity(changed,source).cases_equal_and_valid,9);
  }
});

test('refuses missing cases, wrong request, bad mix and duplicates',()=>{
  const source=corpus(), cases=responses(source);
  assert.throws(()=>checkAllParity(cases.slice(1),source));
  const duplicate=structuredClone(cases); duplicate[1]=duplicate[0];
  assert.throws(()=>checkAllParity(duplicate,source));
  const changed=structuredClone(cases); changed[0].request.query.page=2;
  assert.throws(()=>checkAllParity(changed,source));
  const wrong=corpus(); wrong.cases[0].request.kind='search';
  assert.throws(()=>checkAllParity(responses(wrong),wrong));
});

test('offline command supports all ten and fails closed on differences',()=>{
  const source=corpus(), cases=responses(source), directory=mkdtempSync(join(tmpdir(),'all-parity-'));
  const run=()=>{
    const path=join(directory,'input.json'); writeFileSync(path,JSON.stringify({corpus:source,cases}));
    const fd=openSync(path,'r');
    try { return spawnSync(process.execPath,['scripts/evaluation/k6/comparison_search_parity_cli.mjs','--all'],{stdio:[fd,'pipe','pipe'],encoding:'utf8',timeout:10000}); }
    finally { closeSync(fd); }
  };
  try {
    const good=run(); assert.equal(good.status,0); assert.equal(JSON.parse(good.stdout).cases_checked,10);
    cases[9].b.status=404; assert.equal(run().status,2);
  } finally { rmSync(directory,{recursive:true,force:true}); }
});
