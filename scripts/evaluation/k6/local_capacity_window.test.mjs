import { test } from 'node:test';
import assert from 'node:assert/strict';
import { localCapacityWindow } from './local_capacity_window.js';

test('formal timing stays intact and short mode fails closed for deployed runners', () => {
  const profile = {warmup_seconds: 60, measured_seconds: 300};
  assert.deepEqual(localCapacityWindow({}, true, profile), profile);
  assert.deepEqual(localCapacityWindow({}, false, profile), profile);
  assert.deepEqual(localCapacityWindow({CLIP_CAPACITY_LOCAL_SHORT: 'true'}, false, profile),
    {warmup_seconds: 10, measured_seconds: 60});
  assert.throws(() => localCapacityWindow({CLIP_CAPACITY_LOCAL_SHORT: 'true'}, true, profile));
  assert.throws(() => localCapacityWindow({CLIP_CAPACITY_LOCAL_SHORT: 'false'}, false, profile));
});
