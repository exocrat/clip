// Offline-only comparison of supplied JSON on stdin; never collects responses.
import { readSync, writeSync } from 'node:fs';
import { checkSearchParity } from './comparison_search_parity.js';

const limit = 5_000_000;
try {
  const chunks = [];
  let total = 0;
  while (true) {
    const chunk = Buffer.alloc(Math.min(65_536, limit + 1 - total));
    const count = readSync(0, chunk, 0, chunk.length, null);
    if (count === 0) break;
    total += count;
    if (total > limit) throw Error('input_too_large');
    chunks.push(chunk.subarray(0, count));
  }
  const input = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  if (!input || typeof input !== 'object' || Array.isArray(input) ||
      Object.keys(input).sort().join(',') !== 'cases,corpus') throw Error('invalid_input');
  const result = checkSearchParity(input.cases, input.corpus);
  writeSync(1, `${JSON.stringify(result)}\n`);
  if (!result.all_equal_and_valid) process.exitCode = 2;
} catch (_) {
  writeSync(2, 'Search parity input invalid; no workload started\n');
  process.exitCode = 2;
}
