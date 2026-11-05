import {readFile}from'node:fs/promises';
import vm from'node:vm';
import assert from'node:assert/strict';
const src=await readFile(new URL('../../scripts/evaluation/nfr05_browser.mjs',import.meta.url),'utf8');
let expression=src.match(/const script = `(\(async \(\) => \{ const form[\s\S]*?)`;/)?.[1];assert.ok(expression);expression=expression.replace('${JSON.stringify(messageText)}',JSON.stringify('controlled synthetic draft'));
async function run(allow){let sent=0;const button={disabled:true};const input={disabled:false,dispatchEvent(){button.disabled=!allow;}};const form={querySelector(s){return s.startsWith('textarea')?input:button;},requestSubmit(){sent++;}};class TextArea{};Object.defineProperty(TextArea.prototype,'value',{set(value){this.text=value;}});const result=await vm.runInNewContext(expression,{document:{querySelector(){return form;}},HTMLTextAreaElement:TextArea,Event:class{},requestAnimationFrame(cb){queueMicrotask(cb);}});return {result,sent};}
assert.deepEqual(await run(true),{result:true,sent:1});assert.deepEqual(await run(false),{result:false,sent:0});console.log('2 chat submission checks passed; zero browser or network actions');

// These are the actual Python CLI receipt field names, without credentials.
const {validateIdentityReceipt}=await import('../../scripts/evaluation/nfr05_preflight.mjs');
const receipt={infrastructure_preflight_valid:true,aws_identity_verified:true,https_liveness_verified:true,origin_dns_to_load_balancer_verified:true,session_identity:{session_identity_verified:true,regular_account_verified:true,test_user_id_matches:true,session_expiry_checked:true}};
validateIdentityReceipt(receipt);
for(const key of ['infrastructure_preflight_valid','aws_identity_verified','https_liveness_verified','origin_dns_to_load_balancer_verified'])assert.throws(()=>validateIdentityReceipt({...receipt,[key]:false}),/preflight_incomplete/);
assert.throws(()=>validateIdentityReceipt({...receipt,session_identity:{...receipt.session_identity,regular_account_verified:false}}),/preflight_incomplete/);
assert.throws(()=>validateIdentityReceipt({live_target_checked:true,session_identity:receipt.session_identity}),/preflight_incomplete/);
console.log('7 chat receipt contract checks passed');

const recordBody=src.match(/const record = \(role, event, correlation, timestamp\) => \{([\s\S]*?)\n  \};/)[1];
const row={submittedNs:null,displayedNs:null};
const record=vm.runInNewContext(`(role,event,correlation,timestamp)=>{${recordBody}}`,{rows:[row],correlationIndex:new Map([['controlled-hash',0]]),listeners:new Map(),nsNumber:Number});
record('recipient','submitted','controlled-hash',1n);
record('sender','displayed','controlled-hash',2n);
assert.equal(row.submittedNs,null);assert.equal(row.displayedNs,null);
record('sender','submitted','controlled-hash',10n);
record('recipient','displayed','controlled-hash',20n);
assert.deepEqual(row,{submittedNs:10,displayedNs:20});
console.log('Sender rendering cannot count as recipient delivery: passed');

// Reproduce the actual lifecycle failure: a preparation connection's focus
// setting disappears on detach. The measurement connection must own its own.
const classSource=src.slice(src.indexOf('class CdpPage {'),src.indexOf('\nconst observerScript ='));
let active=false;
class FakeSocket{
 static OPEN=1;
 constructor(){this.readyState=1;this.listeners=new Map();queueMicrotask(()=>this.fire('open',{}));}
 addEventListener(name,callback){const a=this.listeners.get(name)||[];a.push(callback);this.listeners.set(name,a);}
 fire(name,event){for(const cb of this.listeners.get(name)||[])cb(event);}
 send(raw){const m=JSON.parse(raw);if(m.method==='Emulation.setFocusEmulationEnabled')active=m.params.enabled;queueMicrotask(()=>this.fire('message',{data:JSON.stringify({id:m.id,result:{}})}));}
 close(){active=false;this.readyState=3;this.fire('close',{});}
}
const Cdp=vm.runInNewContext(classSource+'\nCdpPage',{WebSocket:FakeSocket,setTimeout,clearTimeout,JSON,Error,Promise,process,HASH:/^[a-f0-9]{64}$/});
const prep=new FakeSocket();active=true;prep.close();assert.equal(active,false);
const measured=new Cdp('ws://synthetic.invalid','recipient',()=>{});
await measured.connect();assert.equal(active,true,'measurement must retain its own active-client emulation');
measured.close();assert.equal(active,false,'closing the measurement releases the emulation');
console.log('Active-client state survives preparation handoff and is released on close: passed');
