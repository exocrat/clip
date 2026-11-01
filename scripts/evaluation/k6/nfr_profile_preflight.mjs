/** Offline-only CLI: read one bounded local draft and print a sanitized result. */
import { readFileSync, statSync } from 'node:fs';
import { validateNfrDraft } from './nfr_profile_preflight.js';

try {
  if (process.argv.length !== 4) throw Error('invalid_arguments');
  const [, , nfr, path] = process.argv;
  if (statSync(path).size > 65536) throw Error('input_too_large');
  const draft = JSON.parse(readFileSync(path, 'utf8'));
  process.stdout.write(`${JSON.stringify(validateNfrDraft(draft, nfr))}\n`);
} catch (_) {
  process.stderr.write('NFR draft preflight failed; no workload was started\n');
  process.exitCode = 2;
}
