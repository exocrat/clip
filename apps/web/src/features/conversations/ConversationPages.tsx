import { createContext, useCallback, useContext, useEffect, useRef, useState, type PropsWithChildren } from 'react';
import { Link, useNavigate } from 'react-router';
import { Button } from '../../shared/ui';
import type { ConversationEntry, ConversationSummary, KeyBundle } from '../../../../../contracts/generated/types.gen';
import { ConversationApiError, type ConversationApi } from './api';
import { ConversationListingSelection, isSellerSaleListingConversation, type ListingSelectionPort } from './ConversationListingSelection';
import { ConversationListingDoneDeal, type ListingAvailabilityPort } from './ConversationListingDoneDeal';
import { ConversationContactPreparation } from './ConversationContactPreparation';
import { ConversationCryptoError, ConversationKeyChangeRequiredError, ConversationKeyStateLostError,
  KeyRegistrationAcknowledgementRequiredError, type ConversationReceiveContext } from './crypto';
import { ConversationInbox, type ConversationInboxFilters, type ConversationInboxItem } from './ConversationInbox';
import { ConversationThread, type ConversationDisplayEntry, type ConversationKeyUiState } from './ConversationThread';
import { openIndexedDbConversationSession, type ConversationSession } from './relay';

/** Identity supplies this only after establishing a real authenticated session.
 * No component accepts a user ID from route/search/form input as caller identity.
 */
export type ConversationPageRuntime = { userId: string; api: ConversationApi; listingSelection: ListingSelectionPort;
  listingAvailability: ListingAvailabilityPort };
const RuntimeContext = createContext<ConversationPageRuntime | null>(null);

export function ConversationPageRuntimeProvider({ runtime, children }: PropsWithChildren<{ runtime: ConversationPageRuntime | null }>) {
  return <RuntimeContext.Provider value={runtime}>{children}</RuntimeContext.Provider>;
}

export function ConversationInboxPage() {
  const runtime = useContext(RuntimeContext);
  if (!runtime) return <p role="status">Sign in to load your conversations. The authenticated session is not connected here yet.</p>;
  // A new account gets fresh page state before its first asynchronous read.
  return <ConversationInboxSession key={runtime.userId} />;
}

function ConversationInboxSession() {
  const runtime = useContext(RuntimeContext);
  const navigate = useNavigate();
  const [items, setItems] = useState<ConversationInboxItem[]>([]);
  const [loading, setLoading] = useState(Boolean(runtime));
  const [loadError, setLoadError] = useState(false);
  const [pageNumber, setPageNumber] = useState(1);
  const [filters, setFilters] = useState<ConversationInboxFilters>({
    view: 'all',
    sort: 'last_activity_desc',
  });
  const [hasNextPage, setHasNextPage] = useState(false);
  const activeRequest = useRef<AbortController | null>(null);
  const requestGeneration = useRef(0);
  const refresh = useCallback(async (options: { silent?: boolean } = {}) => {
    if (!runtime || (options.silent && activeRequest.current)) return;
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    const generation = ++requestGeneration.current;
    if (!options.silent) setLoading(true);
    try {
      const result = await runtime.api.listMine({ ...filters, page: pageNumber }, controller.signal);
      if (controller.signal.aborted || generation !== requestGeneration.current) return;
      setItems(result.items.map((summary) => toInboxItem(summary, runtime.userId)));
      setHasNextPage(result.has_next);
      setLoadError(false);
    } catch {
      if (controller.signal.aborted || generation !== requestGeneration.current) return;
      setLoadError(true);
      throw new ConversationApiError(0, 'transport');
    } finally {
      if (generation === requestGeneration.current) {
        activeRequest.current = null;
        if (!options.silent) setLoading(false);
      }
    }
  }, [filters, pageNumber, runtime]);

  const changeFilters = useCallback((next: ConversationInboxFilters) => {
    setFilters(next);
    setPageNumber(1);
  }, []);

  useEffect(() => {
    if (!runtime || typeof document === 'undefined') return;

    const pollIntervalMs = 2_000;
    const maxBackoffMs = 30_000;
    let delay = pollIntervalMs;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let disposed = false;
    const visible = () => document.visibilityState === 'visible';
    const schedule = () => {
      if (disposed || !visible()) return;
      timer = setTimeout(() => { void poll(); }, delay);
    };
    const poll = async () => {
      if (disposed || !visible()) return;
      if (timer) clearTimeout(timer);
      try {
        await refresh({ silent: true });
        delay = pollIntervalMs;
      } catch {
        delay = Math.min(delay * 2, maxBackoffMs);
      }
      schedule();
    };
    const refreshNow = () => {
      if (visible()) {
        if (timer) clearTimeout(timer);
        void poll();
      } else if (timer) clearTimeout(timer);
    };

    void refresh().catch(() => undefined);
    schedule();
    document.addEventListener('visibilitychange', refreshNow);
    window.addEventListener('focus', refreshNow);
    return () => {
      disposed = true;
      activeRequest.current?.abort();
      if (timer) clearTimeout(timer);
      document.removeEventListener('visibilitychange', refreshNow);
      window.removeEventListener('focus', refreshNow);
    };
  }, [runtime, refresh]);
  if (!runtime) return <p role="status">Sign in to load your conversations. The authenticated session is not connected here yet.</p>;
  return <ConversationInbox conversations={items} loading={loading} loadError={loadError} onRefresh={refresh}
    renderSellerListingAction={(listingId) => <ConversationListingDoneDeal listingId={listingId} availability={runtime.listingAvailability} />}
    filters={filters} onFiltersChange={changeFilters}
    page={pageNumber} hasNextPage={hasNextPage} onPageChange={setPageNumber}
    onOpen={(id) => navigate(`/my/conversations/${encodeURIComponent(id)}`)} />;
}

function toInboxItem(summary: ConversationSummary, userId: string): ConversationInboxItem {
  const initiated = summary.initiator_user_id === userId;
  const role = summary.origin_kind === 'sale_listing'
    ? (initiated ? 'buyer' : 'seller')
    : (initiated ? 'request responder' : 'request author');
  return { conversation_id: summary.conversation_id,
    label: summary.origin_kind === 'sale_listing' ? 'Sale listing conversation' : 'Wanted request conversation',
    role, last_activity_at: summary.last_activity_at, unread_count: summary.unread_count,
    origin_kind: summary.origin_kind, origin_id: summary.origin_id,
    counterparty_user_id: summary.counterparty_user_id,
    current_offer: summary.current_offer
      ? { amount_paise: summary.current_offer.amount_paise, status: summary.current_offer.status }
      : null };
}

/** Process peer recovery traffic and return the original message to annotate, if it was not decryptable. */
export async function processProtocolControlEntry(
  entry: ConversationEntry,
  userId: string,
  conversationId: string,
  session: ConversationSession,
): Promise<string | null> {
  if (entry.kind !== 'protocol_control' || entry.sender_user_id === userId) return null;
  if (!entry.envelope || !entry.recovery_target || !session.history) {
    throw new ConversationCryptoError('Recovery control metadata is incomplete');
  }
  const target = entry.recovery_target;
  const outcome = await session.crypto.receiveProtocolEntry({
    conversation_id: conversationId,
    message_id: entry.entry_id,
    sequence: entry.sequence,
    sender_user_id: entry.sender_user_id,
    sender_device_id: 1,
    expected_sender_key_version: entry.envelope.sender_key_version ?? 0,
    expected_recipient_key_version: entry.envelope.recipient_key_version ?? 0,
    envelope: entry.envelope,
    recovery_target: target,
  }, session.history);
  if (outcome === 'pending') throw new ConversationCryptoError('Recovery control is still pending');
  return entry.envelope.sdk_message_type === 'retry_request' ? target.entry_id : null;
}

type ReadyConversation = { summary: ConversationSummary; session: ConversationSession; ownKey: KeyBundle; peerId: string; peerKeyVersion: number };

export function ConversationDetailPage({ conversationId }: { conversationId: string | undefined }) {
  const runtime = useContext(RuntimeContext);
  if (!runtime) return <p role="status">Sign in to view this conversation. The authenticated session is not connected here yet.</p>;
  // Remount on account/thread change to discard decrypted UI state, drafts and
  // late asynchronous updates. Session cleanup closes crypto; stored keys remain.
  return <ConversationDetailSession key={`${runtime.userId}:${conversationId ?? ''}`} conversationId={conversationId} />;
}

function ConversationDetailSession({ conversationId }: { conversationId: string | undefined }) {
  const runtime = useContext(RuntimeContext);
  const [ready, setReady] = useState<ReadyConversation | null>(null);
  const [authorizedSummary, setAuthorizedSummary] = useState<ConversationSummary | null>(null);
  const [entries, setEntries] = useState<ConversationDisplayEntry[]>([]);
  const decryptionFailureIds = useRef(new Set<string>());
  const [recoveredPending, setRecoveredPending] = useState<{ operationId: string; text: string } | null>(null);
  const [readSequence, setReadSequence] = useState(0);
  const [loading, setLoading] = useState(true);
  const [keyState, setKeyState] = useState<ConversationKeyUiState>({ kind: 'error' });
  const cursor = useRef(0);
  const generation = useRef(0);
  const activeSession = useRef<ConversationSession | null>(null);
  const initializing = useRef<number | null>(null);
  const readinessInFlight = useRef(false);

  const initialize = useCallback(async (acknowledgeHistoryLoss = false, token = generation.current) => {
    if (!runtime || !conversationId || initializing.current === token) return;
    initializing.current = token;
    setLoading(true);
    setReady(null);
    setAuthorizedSummary(null);
    try {
      const previous = activeSession.current;
      activeSession.current = null;
      if (previous) await previous.stop();
      // Authorize the exact route through the server before opening local history.
      const summary = await runtime.api.readSummary(conversationId);
      if (generation.current !== token) return;
      // This authorized summary describes the caller's role and *their peer*,
      // not a fixed initiator/owner pair. For an origin owner both peer and
      // initiator are the other account; the owner's own ID is not repeated.
      const callerMatchesRole = summary.caller_role === 'initiator'
        ? summary.initiator_user_id === runtime.userId
        : summary.caller_role === 'origin_owner' && summary.initiator_user_id !== runtime.userId
          && summary.counterparty_user_id === summary.initiator_user_id;
      if (summary.conversation_id !== conversationId ||
        !callerMatchesRole || summary.counterparty_user_id === runtime.userId) {
        throw new ConversationApiError(404, 'http');
      }
      setAuthorizedSummary(summary);
      const session = await openIndexedDbConversationSession(runtime.userId, conversationId, runtime.api,
        acknowledgeHistoryLoss ? { acknowledgeUnrecoverableHistoryRisk: true } : {});
      if (generation.current !== token) { await session.stop(); return; }
      activeSession.current = session;
      const [ownKey, members] = await Promise.all([runtime.api.readOwnKey(), runtime.api.readMemberKeys(conversationId)]);
      if (generation.current !== token) return;
      if (!ownKey || ownKey.user_id !== runtime.userId) throw new ConversationCryptoError('Own conversation key is unavailable');
      const peerId = summary.counterparty_user_id;
      const peerKey = members.members.filter((member) => member.user_id === peerId).sort((a, b) => b.key_version - a.key_version)[0];
      if (!peerKey) throw new ConversationCryptoError('Participant key is unavailable');
      setReady({ summary, session, ownKey, peerId, peerKeyVersion: peerKey.key_version });
      const resumed = await session.crypto.resumeParticipantSession({ userId: peerId, keyVersion: peerKey.key_version });
      if (!resumed) {
        const bundle = await runtime.api.consumeMemberPrekeys(conversationId, { operation_id: crypto.randomUUID() });
        await session.crypto.establishParticipantSession(bundle, { userId: peerId, keyVersion: bundle.key_bundle.key_version });
      }
      if (generation.current !== token) { await session.stop(); return; }
      setKeyState({ kind: 'ready' });
      const state = await runtime.api.readState(conversationId);
      setReadSequence(state.own_last_read_sequence);
      setLoading(false);
    } catch (error) {
      if (generation.current !== token) return;
      if (error instanceof KeyRegistrationAcknowledgementRequiredError) setKeyState({ kind: 'registration_acknowledgement_required' });
      else if (error instanceof ConversationKeyStateLostError) setKeyState({ kind: 'key_state_lost' });
      else if (error instanceof ConversationKeyChangeRequiredError) setKeyState({ kind: 'key_change', participant_label: 'The other participant' });
      else if (error instanceof ConversationApiError && error.reason === 'peer_key_not_registered') setKeyState({ kind: 'waiting_for_peer_key' });
      else setKeyState({ kind: 'error' });
      setLoading(false);
    } finally {
      if (initializing.current === token) initializing.current = null;
    }
  }, [conversationId, runtime]);

  useEffect(() => {
    const token = ++generation.current;
    cursor.current = 0;
    decryptionFailureIds.current.clear();
    void initialize(false, token).catch(() => undefined);
    return () => {
      generation.current++;
      const session = activeSession.current;
      activeSession.current = null;
      if (session) void session.stop();
    };
  }, [initialize]);

  const refresh = useCallback(async () => {
    // Reuse the thread's visible-only, non-overlapping polling. While waiting,
    // read only readiness: do not recreate keys/sessions or consume prekeys.
    if (runtime && conversationId && keyState.kind === 'waiting_for_peer_key') {
      if (readinessInFlight.current || initializing.current === generation.current) return;
      readinessInFlight.current = true;
      const token = generation.current;
      try {
        await runtime.api.readMemberKeys(conversationId);
        if (generation.current === token) await initialize(false, token);
      } catch (error) {
        if (generation.current !== token) return;
        if (!(error instanceof ConversationApiError && error.reason === 'peer_key_not_registered')) {
          setKeyState({ kind: 'error' });
          throw error;
        }
      } finally {
        readinessInFlight.current = false;
      }
      return;
    }
    if (!runtime || !conversationId || !ready?.session.history || keyState.kind !== 'ready') return;
    // A response may arrive after logout/navigation closed this session. Do not
    // read its history or process protocol traffic after that boundary changes.
    const token = generation.current;
    const isCurrent = () => generation.current === token && activeSession.current === ready.session;
    const history = ready.session.history;
    const observedDecryptionFailureIds = new Set(decryptionFailureIds.current);
    let after = cursor.current;
    const visible: ConversationDisplayEntry[] = [];
    for (let pageCount = 0; pageCount < 100; pageCount++) {
      const page = await runtime.api.readEntries(conversationId, after);
      if (!isCurrent()) return;
      const local = await history.read();
      if (!isCurrent()) return;
      const pending = local.sent.find((item) => item.confirmation === null);
      setRecoveredPending(pending ? { operationId: pending.request.operation_id, text: pending.request.text } : null);
      for (const entry of page.items) {
        if (entry.kind === 'protocol_control') {
          // Recovery controls are protocol traffic, not chat bubbles. The SDK
          // validates/handles them; only an authenticated retry request reports
          // that the original sender's message was not decryptable.
          const failedEntryId = await processProtocolControlEntry(entry, runtime.userId, conversationId,
            ready.session);
          if (!isCurrent()) return;
          if (failedEntryId) observedDecryptionFailureIds.add(failedEntryId);
          continue;
        }
        const display = await decryptEntry(entry, runtime.userId, ready, local.sent,
          (context) => ready.session.receiveText(context));
        if (!isCurrent()) return;
        if (display) visible.push(display);
      }
      after = page.scanned_through_sequence;
      // Advance only after every visible payload on this page has been verified
      // and decrypted; otherwise a transient crypto/storage error could skip it.
      cursor.current = after;
      if (!page.has_more) break;
    }
    decryptionFailureIds.current = observedDecryptionFailureIds;
    setEntries((current) => {
      const byId = new Map(current.map((item) => [item.entry_id, item]));
      for (const item of visible) byId.set(item.entry_id, item);
      for (const id of observedDecryptionFailureIds) {
        const original = byId.get(id);
        if (original && original.sender_user_id === runtime.userId) {
          byId.set(id, { ...original, delivery_notice: 'recipient_unable_to_decrypt' });
        }
      }
      return [...byId.values()].sort((a, b) => a.sequence - b.sequence);
    });
  }, [conversationId, initialize, keyState.kind, ready, runtime]);

  const send = useCallback(async (text: string, operationId: string) => {
    if (!runtime || !conversationId || !ready) throw new ConversationCryptoError('Conversation is not ready');
    try {
      await ready.session.sendText({ conversation_id: conversationId, operation_id: operationId,
        recipient_user_id: ready.peerId, client_timestamp_ms: Date.now(), sender_key_version: ready.ownKey.key_version,
        recipient_key_version: ready.peerKeyVersion, text });
    } catch (error) {
      if (error instanceof ConversationCryptoError) {
        try { await ready.session.crypto.resumeParticipantSession({ userId: ready.peerId, keyVersion: ready.peerKeyVersion }); }
        catch (identityError) {
          if (identityError instanceof ConversationKeyChangeRequiredError) setKeyState({ kind: 'key_change', participant_label: 'The other participant' });
        }
      }
      throw error;
    }
    await refresh();
  }, [conversationId, ready, refresh, runtime]);

  const retry = useCallback(async (operationId: string) => {
    if (!ready) throw new ConversationCryptoError('Conversation is not ready');
    try { await ready.session.relay.retrySend(operationId); }
    catch (error) {
      try { await ready.session.crypto.resumeParticipantSession({ userId: ready.peerId, keyVersion: ready.peerKeyVersion }); }
      catch (identityError) {
        if (identityError instanceof ConversationKeyChangeRequiredError) setKeyState({ kind: 'key_change', participant_label: 'The other participant' });
      }
      throw error;
    }
    await refresh();
  }, [ready, refresh]);

  const acknowledge = useCallback(async (sequence: number) => {
    if (!runtime || !conversationId) return;
    const result = await runtime.api.acknowledgeDisplayed(conversationId, sequence);
    setReadSequence(result.own_last_read_sequence);
  }, [conversationId, runtime]);

  const acceptChangedKey = useCallback(async () => {
    if (!runtime || !conversationId || !ready) return;
    const bundle = await runtime.api.consumeMemberPrekeys(conversationId, { operation_id: crypto.randomUUID() });
    await ready.session.crypto.acceptDirectoryKeyChange(bundle, { userId: ready.peerId, keyVersion: bundle.key_bundle.key_version });
    setReady({ ...ready, peerKeyVersion: bundle.key_bundle.key_version });
    setKeyState({ kind: 'ready' });
  }, [conversationId, ready, runtime]);

  if (!runtime) return <p role="status">Sign in to view this conversation. The authenticated session is not connected here yet.</p>;
  if (!conversationId) return <p role="alert">This conversation link is invalid.</p>;
  const pageSummary = authorizedSummary ?? ready?.summary ?? null;
  return <section aria-label="Conversation page">
    <p><Link to="/my/conversations">Back to conversations</Link></p>
    <h2>{pageSummary?.origin_kind === 'sale_listing' ? 'Sale listing conversation' : pageSummary ? 'Wanted request conversation' : 'Private conversation'}</h2>
    {authorizedSummary ? <ConversationContactPreparation key={conversationId} conversationId={conversationId} api={runtime.api} /> : null}
    {authorizedSummary && isSellerSaleListingConversation(authorizedSummary) ? (
      <ConversationListingSelection
        key={`${authorizedSummary.origin_id}:${authorizedSummary.conversation_id}`}
        listingId={authorizedSummary.origin_id}
        conversationId={authorizedSummary.conversation_id}
        buyerId={authorizedSummary.counterparty_user_id}
        selection={runtime.listingSelection}
      />
    ) : null}
    {keyState.kind === 'error' ? <Button disabled={loading} onClick={() => void initialize().catch(() => undefined)} variant="secondary">Retry loading conversation</Button> : null}
    <ConversationThread current_user_id={runtime.userId} entries={entries} key_state={keyState}
      last_read_sequence={readSequence} loading={loading} onRefresh={refresh} onSend={send} onRetry={retry}
      recoveredPending={recoveredPending}
      onAcknowledgeDisplayed={acknowledge} onAcknowledgeKeyRegistration={() => initialize(true)}
      onAcceptChangedKey={keyState.kind === 'key_change' ? acceptChangedKey : undefined} />
  </section>;
}

async function decryptEntry(
  entry: ConversationEntry,
  userId: string,
  ready: ReadyConversation,
  sent: import('./history').LocalSentMessage[],
  receive: (context: ConversationReceiveContext) => Promise<unknown>,
): Promise<ConversationDisplayEntry | null> {
  if (entry.kind === 'protocol_control') return null;
  if (entry.kind === 'contact_share') return { entry_id: entry.entry_id, sequence: entry.sequence,
    sender_user_id: entry.sender_user_id, created_at: entry.created_at,
    text: 'A contact share is available through the contact-sharing flow.', content_deleted: false };
  if (entry.content_deleted) return { entry_id: entry.entry_id, sequence: entry.sequence,
    sender_user_id: entry.sender_user_id, created_at: entry.created_at, text: null, content_deleted: true };
  if (entry.sender_user_id === userId) {
    const local = sent.find((message) => message.confirmation?.message_id === entry.entry_id);
    const pending = sent.find((message) => message.confirmation === null && message.request.client_timestamp_ms === entry.envelope?.client_timestamp_ms &&
      message.request.sender_key_version === entry.envelope?.sender_key_version &&
      message.request.recipient_key_version === entry.envelope?.recipient_key_version);
    if (!local && pending) return null;
    return { entry_id: entry.entry_id, sequence: entry.sequence, sender_user_id: userId,
      created_at: entry.created_at, text: local?.request.text ?? null, content_deleted: false };
  }
  const envelope = entry.envelope;
  if (!envelope || envelope.sender_key_version == null || envelope.recipient_key_version == null) {
    throw new ConversationCryptoError('Message encryption metadata is unavailable');
  }
  const decoded = await receive({ conversation_id: ready.summary.conversation_id, message_id: entry.entry_id,
    sequence: entry.sequence, sender_user_id: entry.sender_user_id, sender_device_id: 1,
    expected_sender_key_version: envelope.sender_key_version, expected_recipient_key_version: envelope.recipient_key_version,
    envelope });
  if (!decoded || typeof decoded !== 'object' || !('text' in decoded) || typeof decoded.text !== 'string') return null;
  return { entry_id: entry.entry_id, sequence: entry.sequence, sender_user_id: entry.sender_user_id,
    created_at: entry.created_at, text: decoded.text, content_deleted: false };
}
