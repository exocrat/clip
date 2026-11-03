// Offline bridge for live_parity.py: bodies enter stdin and never leave this process.
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {comparisonPath} from './comparison_cases.js';
import {correctParityDraftResponse, validExpected} from './comparison_checks.js';
const canonical = v => Array.isArray(v) ? v.map(canonical) : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map(k => [k,canonical(v[k])])) : v;
try {
  const input=JSON.parse(readFileSync(0,'utf8'));
  if (!Array.isArray(input.cases) || input.cases.length !== 10) throw Error('ten_cases_required');
  const kinds=input.cases.map(c => c.request.kind);
  if (kinds.filter(k=>k==='browse').length!==5 || kinds.filter(k=>k==='search').length!==3 || kinds.filter(k=>k==='detail').length!==2) throw Error('case_mix');
  const paths=input.cases.map(c=>comparisonPath(c.request));
  if (input.cases.some(c => c.request.kind === 'search' ? c.expected !== null : !validExpected(c.request,c.expected))) throw Error('incomplete_expected_cases');
  if (input.responses === undefined) {
    process.stdout.write(JSON.stringify({paths}));
  } else {
    if (input.responses.length!==10) throw Error('responses');
    process.stdout.write(JSON.stringify({cases:input.cases.map((c,i)=>({case_id:c.case_id,path_sha256:createHash('sha256').update(paths[i]).digest('hex'),correct:correctParityDraftResponse(input.responses[i].status,input.responses[i].body,c),status:input.responses[i].status,response_sha256:createHash('sha256').update(JSON.stringify(canonical(input.responses[i].body))).digest('hex')}))}));
  }
} catch (_) { process.stderr.write('Parity bridge input invalid\n'); process.exitCode=2; }
