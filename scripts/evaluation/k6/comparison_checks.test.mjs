import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { correctResponse, validExpected, validSearchResponse, equivalentSearchResponses } from './comparison_checks.js';

const id='01b4fbd6-4c3c-44da-a578-6284033a869c';
const row={listing_id:id,title:'Synthetic bicycle',description:'Synthetic item',category_code:'bicycles',category_label:'Bicycles',condition_code:'good',condition_label:'Good',asking_price_paise:10000,original_price_paise:null,negotiable:true,pickup_area:null,available_from:'2026-01-01T00:00:00.000000Z',available_until:null,availability:'available',sensitive_purchase:false,image_ids:[id]};
const request={kind:'search',query:{q:'bicycle',search_mode:'hybrid',category_code:['bicycles']}};
const page={items:[row],page:1,page_size:20,has_next:false};
const copy=value => structuredClone(value);

test('checks expected ordered page, filters, availability, pagination and all fields', () => {
  assert.equal(correctResponse(200,copy(page),request,page),true);
  for (const alter of [
    p => { p.items[0].listing_id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'; },
    p => { p.items[0].availability='unavailable'; },
    p => { p.items[0].category_code='books'; },
    p => { p.items[0].asking_price_paise=20000; },
    p => { p.items[0].image_ids=[]; },
    p => { p.page=2; },
    p => { p.has_next=true; },
    p => { p.items.push(copy(p.items[0])); },
    p => { delete p.items[0].title; },
  ]) { const actual=copy(page); alter(actual); assert.equal(correctResponse(200,actual,request,page),false); }
  assert.equal(correctResponse(401,copy(page),request,page),false);
  assert.equal(correctResponse(200,null,request,page),false);
});

test('detail checks identity and exact fields; expected cases must be valid', () => {
  const detail={...row,proof_available:null}; const query={kind:'detail',listing_id:id};
  assert.equal(correctResponse(200,copy(detail),query,detail),true);
  assert.equal(correctResponse(200,{...detail,proof_available:true},query,detail),false);
  assert.equal(validExpected(query,{...detail,listing_id:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'}),false);
});

test('the expected order is enforced independently of valid page shape', () => {
  const second={...row,listing_id:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'};
  const expected={...page,items:[row,second]};
  const actual={...page,items:[second,row]};
  assert.equal(correctResponse(200,expected,request,expected),true);
  assert.equal(correctResponse(200,actual,request,expected),false);
});

test('search parity checks valid responses and exact ordered content independently of an oracle', () => {
  assert.equal(validSearchResponse(200,copy(page),request),true);
  assert.equal(equivalentSearchResponses(200,copy(page),200,copy(page),request),true);
  const changed=copy(page); changed.items[0].title='Another synthetic title';
  assert.equal(equivalentSearchResponses(200,page,200,changed,request),false);
  const invalid=copy(page); invalid.items[0].category_code='books';
  assert.equal(equivalentSearchResponses(200,invalid,200,invalid,request),false);
  assert.equal(equivalentSearchResponses(200,page,503,page,request),false);
  const second={...row,listing_id:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'};
  assert.equal(equivalentSearchResponses(200,{...page,items:[row,second]},200,{...page,items:[second,row]},request),false);
});
