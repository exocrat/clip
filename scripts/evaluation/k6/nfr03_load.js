import { responseCorrelation } from './request_correlation.js';
// NFR-03 workload. Direct/local preparation stays loopback-only; a reviewed
// coordinator must validate every gate before using its separate real mode.
import http from 'k6/http';
import { localCapacityWindow } from './local_capacity_window.js';
import { plannedArrivalCount } from './core.js';
import execution from 'k6/execution';
import { Counter, Trend } from 'k6/metrics';
import { sha256 } from 'k6/crypto';
import monotonic from 'k6/x/clipmonotonic';
import { approvedApiTarget, comparisonPath, localApiTarget } from './comparison_cases.js';
import { correctResponse, validSearchResponse } from './comparison_checks.js';
import { preliminaryOutcome } from './comparison_outcomes.js';
import { nfr03Order, nfr03CaseIndex } from './nfr03_schedule.js';
import { validWantedItem, validWantedPage } from './nfr03_checks.js';

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const MAX_RECONCILIATION_PAGES = 10;
const exact = (value, keys) => value !== null && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const canonicalJson = value => {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value !== null && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
};
const uuid4 = input => {
  const bytes = sha256(input, 'hex').slice(0, 32).split('').reduce((a, _, i, all) => i % 2 ? [...a, parseInt(all[i - 1] + all[i], 16)] : a, []);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = bytes.map(value => value.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
};

const realMode = __ENV.CLIP_NFR03_REAL_RUN_MODE === 'approved-runner';
if (realMode ? __ENV.CLIP_NFR03_LOCAL_LOAD === 'true' : __ENV.CLIP_NFR03_LOCAL_LOAD !== 'true') throw Error('explicit_load_runner_mode_required');
const target = realMode
  ? approvedApiTarget(__ENV.CLIP_NFR03_REAL_TARGET, __ENV.CLIP_NFR03_REAL_ORIGIN)
  : localApiTarget(__ENV.CLIP_NFR03_LOCAL_TARGET);
const rawProfile = open(realMode ? __ENV.CLIP_NFR03_REAL_PROFILE : __ENV.CLIP_NFR03_LOCAL_PROFILE);
if (rawProfile.length > 5_000_000) throw Error('profile_too_large');
const profile = JSON.parse(rawProfile);
const PROFILE_KEYS = ['version','purpose','nfr_id','configuration','run_id','dataset_fingerprint','fixture_binding_sha256','case_bundle_sha256','rate_rps','warmup_seconds','measured_seconds','drain_seconds','timeout_seconds','retries','capacity','cases','execution_permitted','nfr_accepted'];
const CASES_KEYS = ['browse','search','detail','wanted_request_id','conversation_id','saved_listing_ids','category_code'];
if (!exact(profile, PROFILE_KEYS) || profile.version !== 1 || profile.purpose !== 'nfr-local-preparation' || profile.nfr_id !== 'nfr-03' || !['A','B'].includes(profile.configuration) || profile.execution_permitted !== false || profile.nfr_accepted !== false || profile.rate_rps !== 50 || profile.warmup_seconds !== 60 || profile.measured_seconds !== 300 || profile.drain_seconds !== 5 || profile.timeout_seconds !== 5 || profile.retries !== 0 || !exact(profile.cases, CASES_KEYS) || sha256(canonicalJson(profile.cases), 'hex') !== profile.case_bundle_sha256) throw Error('invalid_nfr03_profile');
for (const key of ['wanted_request_id','conversation_id']) if (!UUID.test(profile.cases[key])) throw Error('invalid_fixture_id');
if (!Array.isArray(profile.cases.saved_listing_ids) || profile.cases.saved_listing_ids.length < 5 || !profile.cases.saved_listing_ids.every(id => UUID.test(id)) || new Set(profile.cases.saved_listing_ids).size !== profile.cases.saved_listing_ids.length) throw Error('invalid_saved_fixture_ids');
const capacity = profile.capacity;
if (!exact(capacity, ['preAllocatedVUs','maxVUs']) || !Number.isSafeInteger(capacity.preAllocatedVUs) || !Number.isSafeInteger(capacity.maxVUs) || capacity.preAllocatedVUs < 1 || capacity.maxVUs < capacity.preAllocatedVUs) throw Error('capacity_required');
if (!Array.isArray(profile.cases.browse) || profile.cases.browse.length !== 5 || !Array.isArray(profile.cases.search) || profile.cases.search.length !== 3 || !Array.isArray(profile.cases.detail) || profile.cases.detail.length !== 2) throw Error('invalid_frozen_case_mix');
const browsePaths = profile.cases.browse.map(item => comparisonPath(item.request));
const searchPaths = profile.cases.search.map(item => comparisonPath(item.request));
const detailPaths = profile.cases.detail.map(item => comparisonPath(item.request));
if (!profile.cases.browse.every(item => correctResponse(200, item.expected, item.request, item.expected)) || !profile.cases.detail.every(item => correctResponse(200, item.expected, item.request, item.expected)) || !profile.cases.search.every(item => item.request.kind === 'search' && item.request.query.search_mode === 'hybrid')) throw Error('invalid_read_case_oracle');
if (realMode && (!/^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$/.test(__ENV.CLIP_NFR03_REAL_RUN_ID || '') || __ENV.CLIP_NFR03_REAL_RUN_ID !== profile.run_id || __ENV.CLIP_NFR03_REAL_CONFIGURATION !== profile.configuration)) throw Error('approved_run_binding_required');
const cookie = realMode ? __ENV.CLIP_REAL_RUN_SESSION_COOKIE : __ENV.CLIP_NFR03_LOCAL_COOKIE;
const csrf = realMode ? __ENV.CLIP_REAL_RUN_CSRF : __ENV.CLIP_NFR03_LOCAL_CSRF;
const origin = realMode ? __ENV.CLIP_NFR03_REAL_ORIGIN : __ENV.CLIP_NFR03_LOCAL_ORIGIN;
if (typeof cookie !== 'string' || !cookie || /[\r\n]/.test(cookie) || typeof csrf !== 'string' || csrf.length < 32 || csrf.length > 128 || /[\r\n]/.test(csrf) || typeof origin !== 'string' || !(realMode ? /^https:\/\/[A-Za-z0-9.-]+(?::443)?$/.test(origin) : /^http:\/\/(?:127\.0\.0\.1|localhost):[1-9][0-9]{0,4}$/.test(origin))) throw Error('explicit_session_csrf_and_origin_required');

const routeOrder = nfr03Order();
const phases = {};
const phase = (seconds, start) => ({ executor: 'constant-arrival-rate', rate: 50, timeUnit: '1s', duration: `${seconds}s`, startTime: `${start}s`, preAllocatedVUs: capacity.preAllocatedVUs, maxVUs: capacity.maxVUs, gracefulStop: '5s' });
const window = localCapacityWindow(__ENV, realMode, profile);
phases.nfr_warmup = phase(window.warmup_seconds, 0);
phases.nfr_measured = phase(window.measured_seconds, window.warmup_seconds + 5);
const boundarySkipped = new Counter('clip_schedule_boundary_skipped');
const issued = new Counter('clip_nfr03_issued');
const outcomes = new Counter('clip_nfr03_outcomes');
const createdRows = new Counter('clip_nfr03_created_rows');
const reconciliationStatus = new Counter('clip_nfr03_reconciliation_status');
const reconciledRows = new Counter('clip_nfr03_reconciled_rows');
const elapsed = new Trend('clip_nfr03_elapsed_ms', true);
const invalidClock = new Counter('clip_nfr03_clock_invalid');
export const options = { scenarios: phases, maxRedirects: 0, summaryTrendStats: ['med','p(95)','p(99)'], systemTags: ['scenario','status','method','error_code'] };

function pageOk(body, size = 20, page = 1) {
  return body && typeof body === 'object' && !Array.isArray(body) && Array.isArray(body.items) && body.page === page && body.page_size === size && typeof body.has_next === 'boolean';
}
function validWanted(body) {
  return validWantedPage(body);
}
function validConversations(body) {
  return pageOk(body) && body.items.some(item => item && item.conversation_id === profile.cases.conversation_id && UUID.test(item.origin_id) && ['sale_listing','wanted_request'].includes(item.origin_kind) && typeof item.unread_count === 'number');
}
function validSaved(body) {
  if (!pageOk(body) || !body.items.every(item => item && UUID.test(item.listing_id) && typeof item.saved_at === 'string' && typeof item.retired === 'boolean')) return false;
  const ids = new Set(body.items.map(item => item.listing_id));
  return profile.cases.saved_listing_ids.every(id => ids.has(id));
}
function validCreate(body, title, description) {
  return body && typeof body === 'object' && UUID.test(body.request_id) && body.title === title && body.description === description && body.category_code === profile.cases.category_code && body.state === 'open' && Number.isSafeInteger(body.revision) && body.revision >= 1;
}

/** Check the designated fixture before writes can move it off page one. */
export function setup() {
  const response = http.get(`${target}/wanted-requests/${profile.cases.wanted_request_id}`, {
    headers: { Accept: 'application/json', Cookie: cookie }, redirects: 0, timeout: '5s',
    tags: { nfr_id: 'nfr-03', configuration: profile.configuration, run_id: profile.run_id,
      phase: 'nfr_preflight', route: 'wanted_fixture' },
  });
  if (response.status !== 200 || response.error_code !== 0) throw Error('wanted_fixture_preflight_failed');
  const body = response.json();
  if (!validWantedItem(body) || body.request_id !== profile.cases.wanted_request_id) throw Error('wanted_fixture_preflight_failed');
}

/** Issue one operation from the fixed 100-step route mix; raw response bodies are never emitted. */
export default function () {
  const phaseName = execution.scenario.name;
  const iteration = execution.scenario.iterationInTest;
  if (execution.scenario.iterationInTest >= plannedArrivalCount(phases[phaseName])) {
    boundarySkipped.add(1, { phase: execution.scenario.name });
    return;
  }
  const kind = routeOrder[iteration % routeOrder.length];
  const caseIndex = nfr03CaseIndex(kind, iteration);
  let path, method = 'GET', payload, expectedCheck;
  let operationId;
  if (kind === 'browse') { path = `${target}${browsePaths[caseIndex]}`; expectedCheck = body => correctResponse(200, body, profile.cases.browse[caseIndex].request, profile.cases.browse[caseIndex].expected); }
  else if (kind === 'search') { path = `${target}${searchPaths[caseIndex]}`; expectedCheck = body => validSearchResponse(200, body, profile.cases.search[caseIndex].request); }
  else if (kind === 'detail') { path = `${target}${detailPaths[caseIndex]}`; expectedCheck = body => correctResponse(200, body, profile.cases.detail[caseIndex].request, profile.cases.detail[caseIndex].expected); }
  else if (kind === 'wanted') { path = `${target}/wanted-requests?page=1&page_size=20`; expectedCheck = validWanted; }
  else if (kind === 'conversations') { path = `${target}/conversations?page=1&page_size=20`; expectedCheck = validConversations; }
  else if (kind === 'saved') { path = `${target}/me/saved-listings?page=1&page_size=20`; expectedCheck = validSaved; }
  else {
    method = 'POST';
    operationId = uuid4(`${profile.run_id}|${profile.configuration}|${phaseName}|${iteration}`);
    const title = `NFR03 ${profile.run_id} ${operationId}`;
    const description = `Synthetic NFR-03 operation ${operationId}; no personal data.`;
    payload = JSON.stringify({ title, description, category_code: profile.cases.category_code, budget_paise: null, operation_id: operationId });
    path = `${target}/wanted-requests`;
    expectedCheck = body => validCreate(body, title, description);
  }
  const tags = { nfr_id: 'nfr-03', configuration: profile.configuration, run_id: profile.run_id, phase: phaseName, route: kind, ...(operationId ? { operation_id: operationId } : {}) };
  tags.sample_index = String(execution.scenario.iterationInTest);
  issued.add(1, tags);
  let outcome = 'transport_error';
  let duration;
  let timerStarted = false;
  try {
    monotonic.start(); timerStarted = true;
    let response;
    try {
      response = http.request(method, path, payload, { headers: { Accept: 'application/json', Cookie: cookie, ...(payload ? { 'Content-Type': 'application/json', 'Origin': origin, 'X-CLIP-Request': '1', 'X-CSRF-Token': csrf } : {}) }, redirects: 0, timeout: '5s', tags });
    } finally { duration = monotonic.stop(); timerStarted = false; }
    Object.assign(tags, responseCorrelation(response, value => sha256(value, 'hex')));
    outcome = preliminaryOutcome(response);
    if (kind === 'wanted_create' && response.status === 201 && response.error_code === 0) outcome = 'requires_correctness_check';
    if (outcome === 'requires_correctness_check') {
      outcome = 'incorrect';
      try {
        const body = response.json();
        if (expectedCheck(body)) {
          outcome = 'correct';
          if (kind === 'wanted_create') createdRows.add(1, { ...tags, created_request_id: body.request_id });
        }
      } catch (_) { /* Preserve fixed failure only. */ }
    }
  } finally {
    if (timerStarted) { try { duration = monotonic.stop(); } catch (_) { /* Missing duration remains visible. */ } }
    if (!Number.isFinite(duration) || duration < 0) invalidClock.add(1, tags); else elapsed.add(duration, { ...tags, outcome });
    outcomes.add(1, { ...tags, outcome });
  }
}

/** Reconcile every scheduled write by its unique synthetic title after measurement. */
export function teardown() {
  const expectedByTitle = new Map();
  for (const [phaseName, scenario] of Object.entries(phases)) {
    const iterations = plannedArrivalCount(scenario);
    for (let iteration = 0; iteration < iterations; iteration += 1) {
      if (routeOrder[iteration % routeOrder.length] !== 'wanted_create') continue;
      const operationId = uuid4(`${profile.run_id}|${profile.configuration}|${phaseName}|${iteration}`);
      expectedByTitle.set(`NFR03 ${profile.run_id} ${operationId}`, operationId);
    }
  }
  const found = new Set();
  const tags = { nfr_id: 'nfr-03', configuration: profile.configuration, run_id: profile.run_id };
  let complete = false;
  try {
    for (let page = 1; page <= MAX_RECONCILIATION_PAGES; page += 1) {
      const response = http.get(`${target}/me/wanted-requests?page=${page}&page_size=100`, {
        headers: { Accept: 'application/json', Cookie: cookie },
        redirects: 0,
        timeout: '5s',
        tags: { ...tags, phase: 'nfr_reconciliation', route: 'wanted_reconcile' },
      });
      if (response.status !== 200 || response.error_code !== 0) break;
      const body = response.json();
      if (!pageOk(body, 100, page)) break;
      let malformed = false;
      for (const item of body.items) {
        if (!item || typeof item.title !== 'string' || typeof item.request_id !== 'string') continue;
        const operationId = expectedByTitle.get(item.title);
        if (!operationId) continue;
        if (!UUID.test(item.request_id) || found.has(operationId)) {
          malformed = true;
          break;
        }
        found.add(operationId);
        reconciledRows.add(1, { ...tags, operation_id: operationId, created_request_id: item.request_id });
      }
      if (malformed) break;
      if (found.size === expectedByTitle.size) {
        complete = true;
        break;
      }
      if (!body.has_next) {
        complete = found.size === expectedByTitle.size;
        break;
      }
    }
  } catch (_) {
    complete = false;
  }
  reconciliationStatus.add(1, { ...tags, status: complete ? 'complete' : 'incomplete' });
}
