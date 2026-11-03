/** Shared bounded NFR-01/02 workload rules; every target is validated separately. */
import { comparisonPath } from './comparison_cases.js';
import { correctResponse } from './comparison_checks.js';
import { sha256 } from 'k6/crypto';

const PROFILE_KEYS = [
  'version', 'purpose', 'nfr_id', 'configuration', 'run_id',
  'dataset_fingerprint', 'case_bundle_sha256', 'rate_rps',
  'warmup_seconds', 'measured_seconds', 'drain_seconds', 'timeout_seconds',
  'retries', 'capacity', 'cases', 'execution_permitted', 'nfr_accepted',
];
const CASE_KEYS = [
  'case_id', 'request', 'expected_status', 'expected', 'query_class',
];
const HASH = /^[0-9a-f]{64}$/;
const exact = (value, keys) => value !== null && typeof value === 'object' &&
  !Array.isArray(value) && Object.keys(value).length === keys.length &&
  keys.every(key => Object.hasOwn(value, key));
const canonicalJson = value => {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value !== null && typeof value === 'object') {
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
};

/** Validate one offline profile while refusing draft-as-authorization claims. */
export function validateNfrProfile(profile) {
  if (!exact(profile, PROFILE_KEYS) || profile.version !== 1 ||
      profile.purpose !== 'nfr-local-preparation' ||
      !['nfr-01', 'nfr-02'].includes(profile.nfr_id) ||
      !['A', 'B'].includes(profile.configuration) ||
      profile.execution_permitted !== false || profile.nfr_accepted !== false ||
      typeof profile.run_id !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$/.test(profile.run_id) ||
      typeof profile.dataset_fingerprint !== 'string' ||
      !/^sha256:[0-9a-f]{64}$/.test(profile.dataset_fingerprint) ||
      !HASH.test(profile.case_bundle_sha256)) throw Error('invalid_nfr_profile');
  const browse = profile.nfr_id === 'nfr-01';
  const count = browse ? 5 : 3;
  const rate = browse ? 20 : 10;
  if (profile.rate_rps !== rate || profile.warmup_seconds !== 60 ||
      profile.measured_seconds !== 300 || profile.drain_seconds !== 5 ||
      profile.timeout_seconds !== 5 || profile.retries !== 0 ||
      !exact(profile.capacity, ['preAllocatedVUs', 'maxVUs']) ||
      !Number.isSafeInteger(profile.capacity.preAllocatedVUs) ||
      !Number.isSafeInteger(profile.capacity.maxVUs) ||
      profile.capacity.preAllocatedVUs < 1 ||
      profile.capacity.maxVUs < profile.capacity.preAllocatedVUs ||
      !Array.isArray(profile.cases) || profile.cases.length !== count) {
    throw Error('nfr_design_or_capacity_mismatch');
  }
  const ids = new Set();
  for (const item of profile.cases) {
    if (!exact(item, CASE_KEYS) || typeof item.case_id !== 'string' ||
        !/^[a-z0-9][a-z0-9._-]{0,79}$/.test(item.case_id) || ids.has(item.case_id) ||
        item.expected_status !== 200 || item.request?.kind !== (browse ? 'browse' : 'search')) {
      throw Error('invalid_nfr_case');
    }
    ids.add(item.case_id);
    comparisonPath(item.request);
    if (browse) {
      if (item.query_class !== null ||
          !correctResponse(200, item.expected, item.request, item.expected)) {
        throw Error('invalid_browse_oracle');
      }
    } else {
      if (!['direct_word', 'related_word', 'meaning_based'].includes(item.query_class) ||
          item.expected !== null || item.request.query.search_mode !== 'hybrid' ||
          item.request.query.page !== 1 || item.request.query.page_size !== 20) {
        throw Error('invalid_search_case');
      }
    }
  }
  if (sha256(canonicalJson(profile.cases), 'hex') !== profile.case_bundle_sha256) {
    throw Error('case_bundle_hash_mismatch');
  }
  if (browse) {
    if (!profile.cases.some(item => (item.request.query.page ?? 1) === 1) ||
        !profile.cases.some(item => item.request.query.page > 1) ||
        !profile.cases.some(item => item.request.query.category_code !== undefined)) {
      throw Error('browse_case_coverage_required');
    }
  } else {
    const classes = profile.cases.map(item => item.query_class).sort();
    if (classes.join(',') !== 'direct_word,meaning_based,related_word') {
      throw Error('search_case_coverage_required');
    }
  }
  return profile;
}

/** Schedule the fixed warm-up and measured windows with an explicit drain. */
export function nfrScenarios(profile) {
  const phase = (duration, startTime) => ({
    executor: 'constant-arrival-rate',
    rate: profile.rate_rps,
    timeUnit: '1s',
    duration: `${duration}s`,
    startTime: `${startTime}s`,
    preAllocatedVUs: profile.capacity.preAllocatedVUs,
    maxVUs: profile.capacity.maxVUs,
    gracefulStop: `${profile.drain_seconds}s`,
  });
  return {
    nfr_warmup: phase(profile.warmup_seconds, 0),
    nfr_measured: phase(
      profile.measured_seconds,
      profile.warmup_seconds + profile.drain_seconds,
    ),
  };
}

/** Separate browse correctness from search HTTP completion and ranking quality. */
export function successfulNfrResponse(status, actual, item, nfr) {
  if (nfr === 'nfr-01') {
    return correctResponse(status, actual, item.request, item.expected);
  }
  // NFR-02 is search latency; Success@5 belongs to the separate NFR-04 check.
  // k6 returns only after the full response body is received; HTTP status is
  // retained as the request outcome, without evaluating ranking quality here.
  return nfr === 'nfr-02' && status === 200;
}

/** Pick one reviewed request case in a stable cycle. */
export function nfrCaseForIteration(cases, iteration) {
  if (!Number.isSafeInteger(iteration) || iteration < 0) throw Error('invalid_iteration');
  return cases[iteration % cases.length];
}
