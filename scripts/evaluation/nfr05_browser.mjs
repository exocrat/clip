#!/usr/bin/env node
/**
 * Observe NFR-05 at the actual conversation UI using two local CDP sessions.
 * Only sanitized event metadata is written; message text is hashed in memory.
 * A reviewed run manifest and a bound concurrent read workload are required.
 */
import { validateIdentityReceipt } from './nfr05_preflight.mjs';
import { createHash, randomUUID } from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';
import { createReadStream } from 'node:fs';
import { access, chmod, constants, mkdtemp, open, readFile, realpath, rename, rm, stat } from 'node:fs/promises';
import { dirname, isAbsolute, join, resolve, sep } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

const SAMPLE_COUNT = 60;
const INTERVAL_NS = 5_000_000_000n;
const DEADLINE_NS = 5_000_000_000n;
const DRAIN_NS = 5_000_000_000n;
const HASH = /^[0-9a-f]{64}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');

function fail(code) {
  throw new Error(code);
}

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (!key.startsWith('--') || index + 1 >= argv.length || key in result) fail('invalid_arguments');
    result[key.slice(2)] = argv[++index];
  }
  const expected = ['sender-cdp', 'sender-target', 'recipient-cdp', 'recipient-target', 'manifest', 'approval', 'output', 'k6'];
  if (Object.keys(result).length !== expected.length || expected.some((key) => !(key in result))) fail('invalid_arguments');
  return result;
}

function localCdpEndpoint(value) {
  const url = new URL(value);
  if (url.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname) || url.username || url.password || url.search || url.hash) fail('cdp_must_be_loopback');
  return url;
}

async function findPage(endpoint, targetId, expectedOrigin, conversationId) {
  const url = new URL('/json/list', endpoint);
  const response = await fetch(url, { signal: AbortSignal.timeout(3000) });
  if (!response.ok) fail('cdp_target_list_failed');
  const targets = await response.json();
  const target = targets.find((item) => item.type === 'page' && item.id === targetId);
  if (!target || typeof target.webSocketDebuggerUrl !== 'string') fail('cdp_page_not_found');
  const pageUrl = new URL(target.url);
  if (pageUrl.origin !== expectedOrigin || !pageUrl.pathname.includes(`/my/conversations/${conversationId}`)) fail('conversation_page_mismatch');
  const socketUrl = new URL(target.webSocketDebuggerUrl);
  if (socketUrl.protocol !== 'ws:' || !['127.0.0.1', 'localhost', '[::1]'].includes(socketUrl.hostname)) fail('cdp_websocket_must_be_loopback');
  return socketUrl.href;
}

class CdpPage {
  constructor(url, role, onObservation) {
    this.url = url;
    this.role = role;
    this.onObservation = onObservation;
    this.nextId = 1;
    this.pending = new Map();
  }

  async connect() {
    this.socket = new WebSocket(this.url);
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('cdp_connect_timeout')), 5000);
      this.socket.addEventListener('open', () => { clearTimeout(timeout); resolve(); }, { once: true });
      this.socket.addEventListener('error', () => { clearTimeout(timeout); reject(new Error('cdp_connect_failed')); }, { once: true });
    });
    this.socket.addEventListener('message', (event) => this.receive(String(event.data)));
    this.socket.addEventListener('close', () => {
      for (const item of this.pending.values()) item.reject(new Error('cdp_disconnected'));
      this.pending.clear();
    });
    await this.send('Runtime.enable');
    await this.send('Page.enable');
    // Model two active conversation clients on one operator's desktop. Keep
    // this setting on the observer's own connection for the entire run:
    // preparation's short-lived CDP connection loses emulation when it closes.
    // This never generates delivery events; real submit/decrypted-DOM events
    // below remain the only timing boundaries. Closing this session resets it.
    await this.send('Page.setWebLifecycleState', { state: 'active' });
    await this.send('Emulation.setFocusEmulationEnabled', { enabled: true });
    await this.send('Runtime.addBinding', { name: '__clipNfr05Emit' });
  }

  receive(raw) {
    let message;
    try { message = JSON.parse(raw); } catch { return; }
    if (message.id && this.pending.has(message.id)) {
      const pending = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) pending.reject(new Error('cdp_command_failed'));
      else pending.resolve(message.result ?? {});
      return;
    }
    if (message.method !== 'Runtime.bindingCalled' || message.params?.name !== '__clipNfr05Emit') return;
    try {
      const payload = JSON.parse(message.params.payload);
      if ((this.role === 'sender' && payload.event !== 'submitted') || (this.role === 'recipient' && payload.event !== 'displayed') || !HASH.test(payload.correlation)) return;
      this.onObservation(this.role, payload.event, payload.correlation, process.hrtime.bigint());
    } catch { /* Ignore malformed observer events without including their contents. */ }
  }

  send(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error('cdp_command_timeout'));
      }, 5000);
      this.pending.set(id, {
        resolve: (value) => { clearTimeout(timer); resolve(value); },
        reject: (error) => { clearTimeout(timer); reject(error); },
      });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(expression) {
    const result = await this.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (result.exceptionDetails || result.result?.subtype === 'error') fail('browser_evaluation_failed');
    return result.result?.value;
  }

  close() {
    if (this.socket?.readyState === WebSocket.OPEN) this.socket.close();
  }
}

const observerScript = `(() => {
  const emit = async (event, value) => {
    const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
    const correlation = [...new Uint8Array(bytes)].map((part) => part.toString(16).padStart(2, '0')).join('');
    window.__clipNfr05Emit(JSON.stringify({ event, correlation }));
  };
  if (window.__clipNfr05Installed) return true;
  window.__clipNfr05Installed = true;
  document.addEventListener('submit', (event) => {
    const form = event.target instanceof HTMLFormElement && event.target.matches('form.conversation-thread__composer') ? event.target : null;
    const input = form?.querySelector('textarea#conversation-message-draft');
    if (input?.value) void emit('submitted', input.value);
  }, true);
  const inspect = () => document.querySelectorAll('ol[aria-label="Messages"] li.conversation-thread__message p.conversation-thread__text').forEach((item) => {
    if (item.dataset.clipNfr05Seen === '1') return;
    item.dataset.clipNfr05Seen = '1';
    if (item.textContent) void emit('displayed', item.textContent);
  });
  new MutationObserver(inspect).observe(document.documentElement, { subtree: true, childList: true, characterData: true });
  inspect();
  return true;
})()`;

function nsNumber(value) {
  const number = Number(value);
  if (!Number.isSafeInteger(number)) fail('monotonic_timestamp_out_of_range');
  return number;
}

function delayUntil(targetNs) {
  const remaining = targetNs - process.hrtime.bigint();
  if (remaining <= 0n) return Promise.resolve();
  return new Promise((resolve) => setTimeout(resolve, Number(remaining / 1_000_000n)));
}

function metricCount(points, name) {
  return points.filter((point) => point.type === 'Point' && point.metric === name).reduce((sum, point) => {
    const value = point.data?.value;
    if (!Number.isSafeInteger(value) || value < 0) fail('invalid_background_metric');
    return sum + value;
  }, 0);
}

async function runBackground(k6Path, profilePath, origin, session, runId, evidencePath) {
  const temporaryDirectory = await mkdtemp(join(tmpdir(), 'clip-nfr05-bg-'));
  const temporaryRaw = join(temporaryDirectory, 'background.jsonl');
  const script = resolve(ROOT, 'scripts/evaluation/k6/nfr05_background.js');
  const child = spawn(k6Path, ['run', '--quiet', '--no-color', '--address', '', '--out', `json=${temporaryRaw}`, script], {
    cwd: ROOT,
    env: {
      PATH: process.env.PATH || '/usr/bin:/bin',
      K6_NO_USAGE_REPORT: 'true',
      CLIP_NFR05_BG_EXECUTION: 'approved-runner',
      CLIP_NFR05_BG_TARGET_ORIGIN: origin,
      CLIP_NFR05_BG_PROFILE: profilePath,
      CLIP_NFR05_BG_RUN_ID: runId,
      CLIP_NFR05_BG_SESSION_COOKIE: session,
    },
    stdio: 'ignore',
  });
  let exitCode = null;
  let spawnError = false;
  let rawLimitExceeded = false;
  const watchdog = setTimeout(() => child.kill('SIGTERM'), 330_000);
  const sizeGuard = setInterval(async () => {
    try {
      if ((await stat(temporaryRaw)).size > 100_000_000) {
        rawLimitExceeded = true;
        child.kill('SIGTERM');
      }
    } catch { /* The output file may not exist before k6 starts. */ }
  }, 200);
  await new Promise((resolve) => {
    child.once('error', () => { spawnError = true; resolve(); });
    child.once('close', (code) => { exitCode = code; resolve(); });
  });
  clearTimeout(watchdog);
  clearInterval(sizeGuard);
  let raw = Buffer.alloc(0);
  let digest;
  try {
    const info = await stat(temporaryRaw);
    if (info.size > 100_000_000) rawLimitExceeded = true;
    else raw = await readFile(temporaryRaw);
  } catch { /* Missing output is retained as an empty incomplete artifact. */ }
  if (rawLimitExceeded) {
    await rename(temporaryRaw, evidencePath);
    digest = createHash('sha256');
    for await (const chunk of createReadStream(evidencePath)) digest.update(chunk);
    digest = digest.digest('hex');
  } else {
    const rawOutput = await open(evidencePath, 'wx', 0o600);
    try { await rawOutput.writeFile(raw); await rawOutput.sync(); }
    finally { await rawOutput.close(); }
    digest = createHash('sha256').update(raw).digest('hex');
  }
  await chmod(evidencePath, 0o400);
  await rm(temporaryDirectory, { recursive: true, force: true });
  let points = [];
  try { if (!rawLimitExceeded) points = raw.toString('utf8').split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line)); }
  catch { points = []; }
  const outcomes = {};
  for (const point of points) {
    if (point.type !== 'Point' || point.metric !== 'clip_nfr05_bg_outcomes') continue;
    const outcome = point.data?.tags?.outcome;
    const value = point.data?.value;
    if (typeof outcome !== 'string' || !/^[a-z_]{1,40}$/.test(outcome) || !Number.isSafeInteger(value) || value < 0) fail('invalid_background_outcome');
    outcomes[outcome] = (outcomes[outcome] || 0) + value;
  }
  const issued = metricCount(points, 'clip_nfr05_bg_issued');
  const requests = metricCount(points, 'http_reqs');
  const dropped = metricCount(points, 'dropped_iterations');
  const completed = Object.values(outcomes).reduce((sum, value) => sum + value, 0);
  const accountingComplete = issued === 3000 && requests === issued && completed === issued;
  const valid = !spawnError && !rawLimitExceeded && exitCode === 0 && accountingComplete && dropped === 0 && outcomes.completed === issued;
  return {
    run_id: runId,
    scheduled_requests: 3000,
    issued_requests: issued,
    http_requests: requests,
    dropped_iterations: dropped,
    raw_limit_exceeded: rawLimitExceeded,
    outcomes,
    accounting_complete: accountingComplete,
    successful_background_load: valid,
    raw_evidence_path: evidencePath,
    raw_evidence_sha256: digest,
  };
}

function validateActionApproval(manifestBytes, approval, manifest) {
  const keys = ['format_version', 'action', 'run_id', 'manifest_sha256', 'authorized_at', 'expires_at', 'review_record'];
  if (!approval || typeof approval !== 'object' || Array.isArray(approval) || Object.keys(approval).sort().join(',') !== keys.sort().join(',')) fail('invalid_nfr05_action_approval');
  if (approval.format_version !== 1 || approval.action !== 'execute_nfr05_browser_run' || approval.run_id !== manifest.run_id || approval.manifest_sha256 !== createHash('sha256').update(manifestBytes).digest('hex') || typeof approval.review_record !== 'string' || !approval.review_record.trim()) fail('nfr05_approval_binding_mismatch');
  const start = Date.parse(approval.authorized_at);
  const expiry = Date.parse(approval.expires_at);
  const now = Date.now();
  if (!Number.isFinite(start) || !Number.isFinite(expiry) || start > now || expiry <= now || expiry <= start) fail('nfr05_approval_expired_or_misordered');
}

function verifyDeployedIdentity(targetPlanPath, expectedUserId, sessionEnv) {
  const python = process.env.CLIP_PYTHON || resolve(ROOT, '.venv/bin/python');
  const result = spawnSync(python, ['-m', 'scripts.evaluation.k6.real_target_preflight', '--plan', targetPlanPath, '--inspect-live', '--session-env', sessionEnv, '--expected-user-id', expectedUserId], {
    cwd: ROOT,
    env: process.env,
    encoding: 'utf8',
    timeout: 60_000,
    maxBuffer: 100_000,
  });
  if (result.error || result.status !== 0) fail('nfr05_live_target_or_session_preflight_failed');
  const receipt = JSON.parse(result.stdout);
  validateIdentityReceipt(receipt);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const manifestBytes = await readFile(args.manifest);
  const manifestText = manifestBytes.toString('utf8');
  const manifest = JSON.parse(manifestText);
  const approvalBytes = await readFile(args.approval);
  const approval = JSON.parse(approvalBytes.toString('utf8'));
  const required = ['nfr_id', 'run_id', 'execution_permitted', 'target_origin', 'conversation_id_sha256', 'background_profile_sha256', 'human_approved', 'profile_path', 'profile_sha256', 'configuration', 'dataset_fingerprint', 'target_plan_path', 'target_plan_sha256', 'sender_user_id', 'recipient_user_id'];
  if (!manifest || required.some((key) => !(key in manifest)) || manifest.nfr_id !== 'nfr-05' || manifest.execution_permitted !== true || manifest.human_approved !== true || !/^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$/.test(manifest.run_id) || !HASH.test(manifest.conversation_id_sha256) || !HASH.test(manifest.background_profile_sha256)) fail('approved_nfr05_manifest_required');
  validateActionApproval(manifestBytes, approval, manifest);
  if (typeof manifest.profile_path !== 'string' || isAbsolute(manifest.profile_path)) fail('invalid_nfr05_profile_reference');
  const profilePath = resolve(ROOT, manifest.profile_path);
  const workloadRoot = resolve(ROOT, 'data/evaluation/workloads');
  if (!profilePath.startsWith(`${workloadRoot}${sep}`) || !HASH.test(manifest.profile_sha256)) fail('invalid_nfr05_profile_reference');
  const profileRealPath = await realpath(profilePath);
  if (!profileRealPath.startsWith(`${workloadRoot}${sep}`)) fail('invalid_nfr05_profile_reference');
  const profileBytes = await readFile(profileRealPath);
  if (createHash('sha256').update(profileBytes).digest('hex') !== manifest.profile_sha256) fail('nfr05_profile_hash_mismatch');
  const profile = JSON.parse(profileBytes.toString('utf8'));
  if (profile.nfr_id !== 'nfr-05' || profile.messages !== SAMPLE_COUNT || profile.warmup_seconds !== 60 || profile.measured_seconds !== 300 || profile.interval_seconds !== 5 || profile.visibility_deadline_seconds !== 5 || profile.execution_permitted !== false) fail('nfr05_profile_mismatch');
  const origin = new URL(manifest.target_origin);
  if (origin.protocol !== 'https:' || origin.origin !== manifest.target_origin) fail('https_origin_required');
  if (typeof manifest.configuration !== 'string' || !['A', 'B'].includes(manifest.configuration) || typeof manifest.dataset_fingerprint !== 'string' || typeof manifest.background_profile_path !== 'string' || typeof manifest.background_load_run_id !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$/.test(manifest.background_load_run_id) || !HASH.test(manifest.target_plan_sha256) || !UUID.test(manifest.sender_user_id) || !UUID.test(manifest.recipient_user_id) || manifest.sender_user_id === manifest.recipient_user_id || !manifest.resource_and_cost_caps?.trim?.() || !manifest.stop_conditions?.trim?.() || !manifest.cleanup_and_retention?.trim?.() || typeof manifest.evidence_path !== 'string' || typeof manifest.background_load_evidence_path !== 'string') fail('background_run_binding_required');
  if (isAbsolute(manifest.evidence_path) || manifest.evidence_path.includes('..')) fail('invalid_nfr05_evidence_binding');
  const evidencePath = resolve(ROOT, manifest.evidence_path);
  if (!evidencePath.startsWith(`${ROOT}${sep}`) || resolve(`${ROOT}`, `${manifest.evidence_path}.background.jsonl`) !== resolve(ROOT, manifest.background_load_evidence_path)) fail('invalid_nfr05_evidence_binding');
  for (const path of [evidencePath, `${evidencePath}.background.jsonl`]) {
    try { await access(path); fail('output_already_exists'); }
    catch (error) { if (error.message === 'output_already_exists') throw error; }
  }
  if (typeof manifest.target_plan_path !== 'string' || isAbsolute(manifest.target_plan_path) || manifest.target_plan_path.includes('..')) fail('invalid_nfr05_target_plan_reference');
  const targetPlanPath = resolve(ROOT, manifest.target_plan_path);
  if (!targetPlanPath.startsWith(`${ROOT}${sep}`)) fail('invalid_nfr05_target_plan_reference');
  const targetPlanBytes = await readFile(targetPlanPath);
  if (createHash('sha256').update(targetPlanBytes).digest('hex') !== manifest.target_plan_sha256) fail('nfr05_target_plan_hash_mismatch');
  const targetPlan = JSON.parse(targetPlanBytes.toString('utf8'));
  if (targetPlan.run_id !== manifest.run_id || targetPlan.configuration !== manifest.configuration || targetPlan.api_origin !== manifest.target_origin || targetPlan.expected_user_id !== manifest.sender_user_id || targetPlan.revisions?.dataset_fingerprint?.replace(/^sha256:/, '') !== manifest.dataset_fingerprint.replace(/^sha256:/, '') || targetPlan.revisions?.application_revision !== manifest.application_revision) fail('nfr05_target_plan_binding_mismatch');
  const senderSession = process.env.CLIP_NFR05_SENDER_SESSION_COOKIE;
  const recipientSession = process.env.CLIP_NFR05_RECIPIENT_SESSION_COOKIE;
  if (typeof senderSession !== 'string' || !/^__Host-clip_session=[A-Za-z0-9._~+/=-]{1,2048}$/.test(senderSession) || typeof recipientSession !== 'string' || !/^__Host-clip_session=[A-Za-z0-9._~+/=-]{1,2048}$/.test(recipientSession)) fail('nfr05_participant_session_missing_or_invalid');
  verifyDeployedIdentity(targetPlanPath, manifest.sender_user_id, 'CLIP_NFR05_SENDER_SESSION_COOKIE');
  verifyDeployedIdentity(targetPlanPath, manifest.recipient_user_id, 'CLIP_NFR05_RECIPIENT_SESSION_COOKIE');
  const backgroundProfilePath = resolve(ROOT, manifest.background_profile_path);
  if (!backgroundProfilePath.startsWith(`${workloadRoot}${sep}`)) fail('invalid_background_profile_reference');
  const backgroundProfileRealPath = await realpath(backgroundProfilePath);
  if (!backgroundProfileRealPath.startsWith(`${workloadRoot}${sep}`)) fail('invalid_background_profile_reference');
  const backgroundProfileBytes = await readFile(backgroundProfileRealPath);
  if (createHash('sha256').update(backgroundProfileBytes).digest('hex') !== manifest.background_profile_sha256) fail('background_profile_hash_mismatch');
  const backgroundProfile = JSON.parse(backgroundProfileBytes.toString('utf8'));
  if (manifest.background_rate_rps !== 10 || manifest.background_window_seconds !== 300 || !backgroundProfile || Object.keys(backgroundProfile).sort().join(',') !== 'capacity,cases,sequence_starts,timeout_seconds' || backgroundProfile.timeout_seconds !== 5 || !Array.isArray(backgroundProfile.cases) || backgroundProfile.cases.length !== 10 || !Number.isSafeInteger(backgroundProfile.capacity?.preAllocatedVUs) || !Number.isSafeInteger(backgroundProfile.capacity?.maxVUs) || backgroundProfile.capacity.preAllocatedVUs < 1 || backgroundProfile.capacity.maxVUs < backgroundProfile.capacity.preAllocatedVUs || !backgroundProfile.sequence_starts || !Number.isSafeInteger(backgroundProfile.sequence_starts.burst)) fail('background_profile_binding_mismatch');
  if (!isAbsolute(args.k6)) fail('absolute_k6_path_required');
  await access(args.k6, constants.X_OK);
  const backgroundSession = senderSession;
  if (resolve(ROOT, args.output) !== evidencePath) fail('nfr05_output_path_mismatch');
  const rawEvidencePath = `${evidencePath}.background.jsonl`;
  const conversationId = process.env.CLIP_NFR05_CONVERSATION_ID;
  if (typeof conversationId !== 'string' || !UUID.test(conversationId) || createHash('sha256').update(conversationId).digest('hex') !== manifest.conversation_id_sha256) fail('conversation_binding_mismatch');
  const senderEndpoint = localCdpEndpoint(args['sender-cdp']);
  const recipientEndpoint = localCdpEndpoint(args['recipient-cdp']);
  if (senderEndpoint.origin === recipientEndpoint.origin) fail('separate_browser_profiles_required');
  const [senderUrl, recipientUrl] = await Promise.all([
    findPage(senderEndpoint, args['sender-target'], origin.origin, conversationId),
    findPage(recipientEndpoint, args['recipient-target'], origin.origin, conversationId),
  ]);
  if (senderUrl === recipientUrl) fail('two_distinct_browser_sessions_required');
  if (manifest.browser_activity_mode !== 'cdp_emulated_active_conversations') fail('active_browser_mode_not_approved');

  const rows = Array.from({ length: SAMPLE_COUNT }, (_, index) => ({ index, correlation: '', submittedNs: null, displayedNs: null, submitFailureNs: null }));
  const correlationIndex = new Map();
  const listeners = new Map();
  const record = (role, event, correlation, timestamp) => {
    // Sender rendering is not delivery. Only the recipient can finish timing.
    if (!((role === 'sender' && event === 'submitted') || (role === 'recipient' && event === 'displayed'))) return;
    const index = correlationIndex.get(correlation);
    if (index === undefined) return;
    const row = rows[index];
    if (event === 'submitted' && row.submittedNs === null) row.submittedNs = nsNumber(timestamp);
    if (event === 'displayed' && row.displayedNs === null) row.displayedNs = nsNumber(timestamp);
    const waiter = listeners.get(`${event}:${correlation}`);
    if (waiter) { listeners.delete(`${event}:${correlation}`); waiter(); }
  };
  const sender = new CdpPage(senderUrl, 'sender', record);
  const recipient = new CdpPage(recipientUrl, 'recipient', record);
  try {
    await Promise.all([sender.connect(), recipient.connect()]);
    await Promise.all([sender.evaluate(observerScript), recipient.evaluate(observerScript)]);
    // An empty draft correctly disables Send. Check editability now, then
    // wait for the real UI to enable Send after each controlled draft is set.
    const ready = await sender.evaluate(`(() => { const form = document.querySelector('section[aria-label="Private conversation"] form.conversation-thread__composer'); const input = form?.querySelector('textarea#conversation-message-draft'); const button = form?.querySelector('button[type="submit"]'); return Boolean(form && input && button && !input.disabled && document.visibilityState === 'visible'); })()`);
    const recipientReady = await recipient.evaluate(`Boolean(document.querySelector('ol[aria-label="Messages"]') && document.visibilityState === 'visible')`);
    if (ready !== true || recipientReady !== true) fail('conversation_ui_not_ready');

    // Both real conversation tabs remain open for the specified warm-up.
    await new Promise((resolve) => setTimeout(resolve, 60_000));
    const backgroundPromise = runBackground(args.k6, backgroundProfileRealPath, origin.origin, backgroundSession, manifest.background_load_run_id, rawEvidencePath);
    const start = process.hrtime.bigint();
    const sends = rows.map(async (row) => {
      const scheduled = start + BigInt(row.index) * INTERVAL_NS;
      await delayUntil(scheduled);
      const messageText = `NFR05 ${manifest.run_id} ${row.index} ${randomUUID()}`;
      const correlation = createHash('sha256').update(messageText).digest('hex');
      row.correlation = correlation;
      correlationIndex.set(correlation, row.index);
      const script = `(async () => { const form = document.querySelector('section[aria-label="Private conversation"] form.conversation-thread__composer'); const input = form?.querySelector('textarea#conversation-message-draft'); const button = form?.querySelector('button[type="submit"]'); if (!form || !input || !button || input.disabled) return false; const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set; setter.call(input, ${JSON.stringify(messageText)}); input.dispatchEvent(new Event('input', { bubbles: true })); await new Promise(resolve => requestAnimationFrame(resolve)); if (button.disabled || input.disabled) return false; form.requestSubmit(); return true; })()`;
      try {
        const submitted = await sender.evaluate(script);
        if (submitted !== true) row.submitFailureNs = nsNumber(process.hrtime.bigint());
      } catch {
        row.submitFailureNs = nsNumber(process.hrtime.bigint());
      }
    });
    await Promise.all(sends);
    await delayUntil(start + BigInt(SAMPLE_COUNT) * INTERVAL_NS + DRAIN_NS);
    const backgroundLoad = await backgroundPromise;
    backgroundLoad.raw_evidence_path = manifest.background_load_evidence_path;

    const samples = rows.map((row) => {
      if (row.submittedNs === null) return { index: row.index, outcome: 'failed', submitted_ns: null, displayed_ns: null };
      if (row.displayedNs !== null) return { index: row.index, outcome: 'displayed', submitted_ns: row.submittedNs, displayed_ns: row.displayedNs };
      return { index: row.index, outcome: 'undisplayed', submitted_ns: row.submittedNs, displayed_ns: null };
    });
    const output = {
      format_version: 1,
      nfr_id: 'nfr-05',
      run_id: manifest.run_id,
      configuration: manifest.configuration,
      target_origin: origin.origin,
      manifest_sha256: createHash('sha256').update(manifestBytes).digest('hex'),
      target_plan_sha256: manifest.target_plan_sha256,
      action_approval_sha256: createHash('sha256').update(approvalBytes).digest('hex'),
      application_revision: manifest.application_revision,
      dataset_fingerprint: manifest.dataset_fingerprint,
      conversation_id_sha256: manifest.conversation_id_sha256,
      background_profile_sha256: manifest.background_profile_sha256,
      clock: 'Node process.hrtime.bigint monotonic at browser event receipt over local CDP',
      warmup_seconds: 60,
      measured_seconds: 300,
      expected_messages: SAMPLE_COUNT,
      interval_seconds: 5,
      deadline_seconds: 5,
      background_load_verified: backgroundLoad.successful_background_load,
      live_target_and_participants_preflighted: true,
      background_load: backgroundLoad,
      nfr_accepted: false,
      samples,
      correlation_sha256_by_index: rows.map(({ index, correlation }) => ({ index, sha256: correlation })),
    };
    const file = await open(evidencePath, 'wx', 0o600);
    await file.writeFile(`${JSON.stringify(output, null, 2)}\n`, 'utf8');
    await file.sync();
    await file.close();
    await chmod(evidencePath, 0o400);
    process.stdout.write(JSON.stringify({ output: args.output, sample_count: samples.length, nfr_accepted: false, background_load_verified: backgroundLoad.successful_background_load }) + '\n');
  } finally {
    sender.close();
    recipient.close();
  }
}

main().catch((error) => {
  process.stderr.write(`NFR-05 browser capture refused or incomplete: ${error?.message || 'unknown_error'}\n`);
  process.exitCode = 2;
});
