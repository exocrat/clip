import assert from 'node:assert/strict';
import test from 'node:test';
import { nfr03Order, nfr03Weights, nfr03CaseIndex } from './nfr03_schedule.js';

test('preserves every reviewed operation count and is independent of A/B/outcomes', () => {
  const order = nfr03Order();
  assert.equal(order.length, 100);
  for (const [route, count] of Object.entries(nfr03Weights)) {
    assert.equal(order.filter(value => value === route).length, count);
  }
  assert.deepEqual(nfr03Order(), order);
});

test('spreads the request classes across prefixes and repeated cycle boundaries', () => {
  const order = [...nfr03Order(), ...nfr03Order()];
  const seen = Object.fromEntries(Object.keys(nfr03Weights).map(key => [key, 0]));
  for (let index = 0; index < order.length; index += 1) {
    seen[order[index]] += 1;
    for (const [route, fraction] of Object.entries(nfr03Weights)) {
      assert.ok(Math.abs(seen[route] - (index + 1) * fraction / 100) < 2);
    }
  }
});


test('each route rotates cases evenly without changing warm-up/measured case counts', () => {
  const order = nfr03Order();
  for (const length of [3000, 15000]) {
    const counts = {browse: Array(5).fill(0), search: Array(3).fill(0), detail: Array(2).fill(0)};
    let priorSearch = -1;
    for (let iteration = 0; iteration < length; iteration++) {
      const kind = order[iteration % 100];
      const index = nfr03CaseIndex(kind, iteration);
      if (Object.hasOwn(counts, kind)) counts[kind][index]++;
      if (kind === 'search') {
        assert.notEqual(index, priorSearch);
        priorSearch = index;
      }
    }
    for (const [kind, values] of Object.entries(counts)) {
      assert.ok(values.every(count => count === length * nfr03Weights[kind] / 100 / values.length));
    }
  }
});
