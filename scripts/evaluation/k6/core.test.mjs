import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { validateProfile, validPage, scenarios, SUMMARY_FIELDS } from './core.js';
const root = new URL('../../../', import.meta.url);
const profile = JSON.parse(readFileSync(new URL('data/evaluation/workloads/local-search-pilot-v1.json',root)));
const item = profile.cases[0];
const row = {listing_id:item.expected_ids[0],title:'Controlled bicycle',description:'Controlled load response',category_code:'bicycles',category_label:'Bicycles',condition_code:'good',condition_label:'Good',asking_price_paise:0,original_price_paise:null,negotiable:false,pickup_area:null,available_from:'2026-01-01T00:00:00.000000Z',available_until:null,availability:'available',sensitive_purchase:false,image_ids:[]};
const page = () => ({items:[{...row}],page:1,page_size:20,has_next:false});
test('profile caps, default/mode query vocabulary and drift against generated summary', () => {
  assert.equal(validateProfile(profile),profile);
  const doc = JSON.parse(readFileSync(new URL('contracts/generated/openapi.json',root)));
  assert.deepEqual([...SUMMARY_FIELDS].sort(),Object.keys(doc.components.schemas.ListingSummary.properties).sort());
  const s = scenarios(profile);
  assert.equal(s.warmup.maxVUs,2); assert.equal(s.measured.maxVUs,2);
  assert.equal(s.measured.startTime,'8s'); assert.equal(s.warmup.gracefulStop,'3s');
  for (const kind of ['browse','keyword','hybrid']) {
    const draft = JSON.parse(readFileSync(new URL(`data/evaluation/workloads/${kind}-nfr-draft-v1.json`,root)));
    assert.equal(validateProfile(draft).purpose,'nfr-draft');
  }
});
for (const edit of [p=>p.rate=3,p=>p.max_vus=3,p=>p.measured_seconds=11,p=>p.timeout_seconds=4,p=>p.cases[0].query.owner_id='other',p=>p.cases[0].query.search_mode='semantic',p=>p.cases[0].query.sort='relevance',p=>p.cases[0].expected_ids=[]]) test(`reject malformed/capped profile ${String(edit)}`, () => {
  const p = structuredClone(profile); edit(p); assert.throws(()=>validateProfile(p));
});
test('valid public shape still requires correct fixture result, page, availability and safe fields', () => {
  assert.equal(validPage(page(),item),true);
  for (const edit of [p=>p.items=[],p=>p.items[0].owner_id='other',p=>p.items[0].availability='unavailable',p=>p.items[0].asking_price_paise=101,p=>p.page=2,p=>p.has_next=true,p=>p.items.push({...p.items[0]}),p=>p.items[0].available_from='2099-01-01T00:00:00.000000Z']) {
    const p=page(); edit(p); assert.equal(validPage(p,item),false);
  }
});


test('arrival budgets cover fractional-rate phases and reject invalid schedules', async () => {
  const { plannedArrivalCount } = await import('./core.js');
  assert.equal(plannedArrivalCount({ rate: 50, duration: '300s', timeUnit: '1s' }), 15000);
  assert.equal(plannedArrivalCount({ rate: 1, duration: '300s', timeUnit: '5s' }), 60);
  assert.throws(() => plannedArrivalCount({ rate: 1, duration: '1s', timeUnit: '5s' }));
});
