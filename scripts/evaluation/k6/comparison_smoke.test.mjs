import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { comparisonPath, localApiTarget } from './comparison_cases.js';

// Exercise the adapter with substituted k6 APIs; this is not a k6 runtime test.
function load(env) {
  const source = readFileSync(new URL('./comparison_smoke.js', import.meta.url), 'utf8')
    .replace(/^import .*;$/gm, '')
    .replace('export const options', 'globalThis.options')
    .replace('export default function ()', 'globalThis.run = function ()');
  const calls = [];
  class Counter { add() {} }
  const context = { __ENV:env, comparisonPath, localApiTarget, validExpected:() => true, correctResponse:() => true, Counter, execution:{scenario:{iterationInTest:0}}, http:{get:(...args) => { calls.push(args); return {status:200,json:() => ({})}; }} };
  vm.runInNewContext(source, context);
  return { context, calls };
}

test('k6 adapter issues one local authenticated request without claiming correctness', () => {
  const {context, calls} = load({CLIP_COMPARISON_LOCAL_TARGET:'http://127.0.0.1:8000', CLIP_COMPARISON_LOCAL_COOKIE:'clip_session_dev=synthetic', CLIP_COMPARISON_LOCAL_CASES:JSON.stringify([{request:{kind:'search',query:{q:'desk',search_mode:'hybrid'}},expected:{}}])});
  assert.equal(context.options.iterations, 1);
  context.run();
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], 'http://127.0.0.1:8000/listings?q=desk&search_mode=hybrid');
  assert.equal(calls[0][1].headers.Cookie, 'clip_session_dev=synthetic');
  assert.equal(calls[0][1].redirects, 0);
});

test('k6 adapter refuses cloud targets and unsafe sessions before HTTP', () => {
  const good = {CLIP_COMPARISON_LOCAL_TARGET:'http://127.0.0.1:8000', CLIP_COMPARISON_LOCAL_COOKIE:'session=x', CLIP_COMPARISON_LOCAL_CASES:JSON.stringify([{request:{kind:'browse',query:{}},expected:{}}])};
  assert.throws(() => load({...good, CLIP_COMPARISON_LOCAL_TARGET:'https://example.com'}));
  assert.throws(() => load({...good, CLIP_COMPARISON_LOCAL_COOKIE:'x\r\ny'}));
  assert.throws(() => load({...good, CLIP_COMPARISON_LOCAL_CASES:'{}'}));
  assert.throws(() => load({...good, CLIP_COMPARISON_LOCAL_CASES:JSON.stringify(Array(11).fill({request:{kind:'browse',query:{}},expected:{}}))}));
  assert.throws(() => load({...good, CLIP_COMPARISON_LOCAL_CASES:JSON.stringify([{request:{kind:'browse',query:{}},expected:{}},{request:{kind:'detail',listing_id:'invalid'},expected:{}}])}));
});

test('k6 adapter supports the integrated /api mount', () => {
  const {context, calls} = load({CLIP_COMPARISON_LOCAL_TARGET:'http://127.0.0.1:5174/api', CLIP_COMPARISON_LOCAL_COOKIE:'clip_session_dev=synthetic', CLIP_COMPARISON_LOCAL_CASES:JSON.stringify([{request:{kind:'browse',query:{}},expected:{}}])});
  context.run();
  assert.equal(calls[0][0], 'http://127.0.0.1:5174/api/listings');
});

test('k6 adapter runs the complete validated batch in order', () => {
  const cases = [{kind:'browse',query:{}},{kind:'search',query:{q:'desk',search_mode:'hybrid'}},{kind:'detail',listing_id:'01b4fbd6-4c3c-44da-a578-6284033a869c'}].map(request => ({request,expected:{}}));
  const {context, calls} = load({CLIP_COMPARISON_LOCAL_TARGET:'http://127.0.0.1:5174/api',CLIP_COMPARISON_LOCAL_COOKIE:'session=x',CLIP_COMPARISON_LOCAL_CASES:JSON.stringify(cases)});
  assert.equal(context.options.iterations, 3);
  for (let i=0;i<3;i++) { context.execution.scenario.iterationInTest=i; context.run(); }
  assert.deepEqual(calls.map(call => call[0]), ['http://127.0.0.1:5174/api/listings','http://127.0.0.1:5174/api/listings?q=desk&search_mode=hybrid','http://127.0.0.1:5174/api/listings/01b4fbd6-4c3c-44da-a578-6284033a869c']);
});
