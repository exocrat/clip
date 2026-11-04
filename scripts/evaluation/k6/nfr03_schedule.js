/** Fixed smooth weighted ordering; preserves the reviewed 100-operation mix.
 * The coordinator hashes/stages this module with the workload. Neither response
 * times nor previous outcomes influence the sequence, and A/B use identical order.
 */
export const nfr03Weights = Object.freeze({
  browse: 30, search: 25, detail: 15, wanted: 10,
  conversations: 10, saved: 9, wanted_create: 1,
});

export function nfr03Order() {
  const entries = Object.entries(nfr03Weights);
  const current = entries.map(() => 0);
  const result = [];
  for (let step = 0; step < 100; step += 1) {
    let best = 0;
    for (let index = 0; index < entries.length; index += 1) {
      current[index] += entries[index][1];
      if (current[index] > current[best]) best = index;
    }
    result.push(entries[best][0]);
    current[best] -= 100;
  }
  return result;
}

const casesPerRoute = Object.freeze({ browse: 5, search: 3, detail: 2 });
const orderedRoutes = nfr03Order();
const countsBefore = {};
const ordinalWithinCycle = orderedRoutes.map(kind => {
  const ordinal = countsBefore[kind] || 0;
  countsBefore[kind] = ordinal + 1;
  return ordinal;
});

/** Rotate cases on each occurrence of their route, rather than grouping one
 * query/filter for a whole two-second cycle. Total per-case counts are unchanged
 * over both frozen windows; input/output never depends on responses or A/B.
 */
export function nfr03CaseIndex(kind, iteration) {
  if (!Number.isSafeInteger(iteration) || iteration < 0 || orderedRoutes[iteration % 100] !== kind) throw Error('invalid_route_iteration');
  if (!Object.hasOwn(casesPerRoute, kind)) return 0;
  const ordinal = Math.floor(iteration / 100) * nfr03Weights[kind] + ordinalWithinCycle[iteration % 100];
  return ordinal % casesPerRoute[kind];
}
