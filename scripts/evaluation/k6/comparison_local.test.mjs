import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { sendLocalCase, runLocalPreparation } from './comparison_local.js';
import { createServer } from 'node:http';

test('sends one real-contract read through an injected session transport', async () => {
  const calls = [];
  const result = await sendLocalCase({target:'http://127.0.0.1:8000', item:{kind:'search',query:{q:'desk',search_mode:'hybrid'}}, sessionCookie:'session=synthetic', send:async (...args) => { calls.push(args); return {status:401}; }});
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], 'http://127.0.0.1:8000/listings?q=desk&search_mode=hybrid');
  assert.equal(calls[0][1].headers.Cookie, 'session=synthetic');
  assert.equal(calls[0][1].redirect, 'error');
  assert.equal(result.status, 401);
});

test('refuses non-loopback targets and unsafe session headers before sending', async () => {
  let calls = 0;
  const send = async () => { calls++; };
  for (const target of ['https://example.com', 'http://localhost:8000', 'http://127.0.0.1:65536', 'http://127.0.0.1:8000/path']) {
    await assert.rejects(sendLocalCase({target, item:{kind:'browse',query:{}}, sessionCookie:'session=x', send}));
  }
  await assert.rejects(sendLocalCase({target:'http://127.0.0.1:8000', item:{kind:'browse',query:{}}, sessionCookie:'x\r\ny', send}));
  assert.equal(calls, 0);
});

test('local batch sends contract paths and never treats HTTP status as verified correctness', async () => {
  const received = [];
  const server = createServer((req, res) => {
    received.push({ url: req.url, cookie: req.headers.cookie });
    res.writeHead(req.url.includes('q=') ? 401 : 200, {'Content-Type':'application/json'});
    res.end('{}');
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const result = await runLocalPreparation({ target:`http://127.0.0.1:${server.address().port}`, cases:[{kind:'browse',query:{}},{kind:'search',query:{q:'desk',search_mode:'hybrid'}}], sessionCookie:'clip_session_dev=synthetic', send:fetch });
    assert.deepEqual(received.map(r => r.url), ['/listings','/listings?q=desk&search_mode=hybrid']);
    assert.ok(received.every(r => r.cookie === 'clip_session_dev=synthetic'));
    assert.deepEqual(result.outcomes.map(o => [o.status,o.correctness]), [[200,'unchecked'],[401,'unchecked']]);
    assert.equal(result.measurement, false);
  } finally {
    await new Promise((resolve, reject) => server.close(err => err ? reject(err) : resolve()));
  }
});

test('batch validates its bound and all cases before making requests', async () => {
  let calls = 0;
  const send = async () => { calls++; return {status:200}; };
  const base = {target:'http://127.0.0.1:8000', sessionCookie:'session=x', send};
  await assert.rejects(runLocalPreparation({...base, cases:Array(11).fill({kind:'browse',query:{}})}));
  await assert.rejects(runLocalPreparation({...base, cases:[{kind:'browse',query:{}},{kind:'detail',listing_id:'invalid'}]}));
  assert.equal(calls, 0);
});

test('local adapter reaches the integrated /api mount', async () => {
  let request;
  await sendLocalCase({target:'http://127.0.0.1:5174/api', item:{kind:'browse',query:{}}, sessionCookie:'clip_session_dev=synthetic', send:async url => { request = url; return {status:200}; }});
  assert.equal(request, 'http://127.0.0.1:5174/api/listings');
});
