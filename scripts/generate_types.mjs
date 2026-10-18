/** Generate TypeScript types only in the Python orchestrator's temporary folder.
 * No SDK/client plugins, remote schema references, or output-directory cleanup.
 */
import { readFile } from 'node:fs/promises';
import { basename, dirname, resolve } from 'node:path';
import { createClient } from '@hey-api/openapi-ts';

const [input, output] = process.argv.slice(2);
if (!input || !output || process.argv.length !== 4 ||
    basename(input) !== 'openapi.json' || basename(output) !== 'types' ||
    dirname(resolve(input)) !== dirname(resolve(output)) ||
    !basename(dirname(resolve(input))).startsWith('clip-contracts-')) {
  throw new Error('Expected the contract generator temporary input/output paths');
}
const schema = JSON.parse(await readFile(input, 'utf8'));

/** Refuse remote/file references before the generator resolves the schema. */
function validateReferences(value) {
  if (!value || typeof value !== 'object') return;
  for (const [key, child] of Object.entries(value)) {
    if (key === '$ref' && (typeof child !== 'string' || !child.startsWith('#/'))) {
      throw new Error('Only local schema references are permitted');
    }
    validateReferences(child);
  }
}
validateReferences(schema);

await createClient({
  input: schema,
  interactive: false,
  logs: { level: 'silent' },
  output: {
    path: output,
    clean: false,
    entryFile: false,
    postProcess: [],
    tsConfigPath: null,
  },
  plugins: [{ name: '@hey-api/typescript', enums: false }],
});
