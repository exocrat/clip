/** Verify revised create contents and exact operation counts without HTTP. */
import assert from 'node:assert/strict';
import { nfr03Kind, nfr03CaseIndex } from './nfr03_schedule.js';
import { validListingCreate } from './nfr03_checks.js';
for (const size of [3000,15000]) {
 const counts={};
 for(let i=0;i<size;i++){const kind=nfr03Kind(i,true);counts[kind]=(counts[kind]||0)+1;if(kind!=='listing_create')nfr03CaseIndex(kind,i);}
 assert.equal(counts.listing_create,size/3000);assert.equal(counts.browse,size*.3-size/3000);assert.equal(counts.wanted_create,size*.01);assert.equal(Object.values(counts).reduce((a,b)=>a+b),size);
}
const command={title:'Controlled scheduled sale listing',description:'Synthetic test content',category_code:'other',condition_code:'good',asking_price_paise:10000,original_price_paise:null,negotiable:false,pickup_area:'Synthetic pickup',available_from:'2030-01-01T00:00:00Z',available_until:null,proof_available:null};
const body={...command,listing_id:'00000000-0000-4000-8000-000000000001',category_label:'Other',condition_label:'Good',availability:'available',sensitive_purchase:false,image_ids:['00000000-0000-4000-8000-000000000002']};
assert.equal(validListingCreate(body,command),true);
for(const patch of [{asking_price_paise:20000},{title:'Wrong title'},{category_code:'wrong'},{condition_code:'wrong'},{available_from:'2030-01-02T00:00:00Z'},{availability:'unavailable'},{image_ids:[]},{listing_id:'invalid'},{extra:'unexpected'}])assert.equal(validListingCreate({...body,...patch},command),false);
console.log('Revised schedule preserves all totals; nine incorrect sale-listing results rejected; zero network requests.');
