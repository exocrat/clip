import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { createHash } from 'node:crypto';
import { responseCorrelation } from './request_correlation.js';

const hash = value => createHash('sha256').update(value).digest('hex');
test('records only a server ID hash and preserves missing/rejected attribution', () => {
  const id = '11111111-1111-4111-8111-111111111111';
  assert.deepEqual(responseCorrelation({headers:{'X-Request-Id':id, 'Set-Cookie':'private'}}, hash), {correlation:'server_id',request_id_sha256:hash(id)});
  assert.deepEqual(responseCorrelation({status:502,headers:{}}, hash), {correlation:'unattributed'});
  assert.deepEqual(responseCorrelation(undefined, hash), {correlation:'unattributed'});
  assert.deepEqual(responseCorrelation({headers:{'X-Request-Id':'private input'}}, hash), {correlation:'invalid_server_id'});
  assert.deepEqual(responseCorrelation({headers:{'X-Request-Id':id,'x-request-id':id}}, hash), {correlation:'unattributed'});
});
