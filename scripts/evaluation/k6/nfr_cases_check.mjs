/** Offline-only CLI: check one selected case set from a bounded local draft. */
import { readFileSync, statSync } from 'node:fs';
import { validateNfrCases } from './nfr_cases_check.js';

try {
  if (process.argv.length !== 4) throw Error('invalid_arguments');
  const [, , nfr, path] = process.argv;
  if (statSync(path).size > 5_000_000) throw Error('input_too_large');
  const bundle = JSON.parse(readFileSync(path, 'utf8'));
  process.stdout.write(`${JSON.stringify(validateNfrCases(bundle, nfr))}\n`);
} catch (_) {
  process.stderr.write('NFR case validation failed; no workload was started\n');
  process.exitCode = 2;
}
