import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Button, MultiChoiceDropdown } from '../../shared/ui';
import type { ConversationListQuery } from './api';
import './ConversationInbox.css';

export type ConversationInboxItem = {
  conversation_id: string;
  label: string;
  role: 'buyer' | 'seller' | 'request responder' | 'request author';
  last_activity_at: string;
  unread_count: number;
  origin_kind?: 'sale_listing' | 'wanted_request';
  origin_id?: string;
  counterparty_user_id?: string;
  current_offer?: { amount_paise: number; status: 'submitted' | 'withdrawn' } | null;
};

export type ConversationInboxFilters = Omit<ConversationListQuery, 'page' | 'page_size'>;

export type ConversationInboxProps = {
  conversations: ConversationInboxItem[];
  loading?: boolean;
  loadError?: boolean;
  onRefresh: () => Promise<void>;
  onOpen: (conversationId: string) => void;
  filters?: ConversationInboxFilters;
  onFiltersChange?: (filters: ConversationInboxFilters) => void;
  page?: number;
  hasNextPage?: boolean;
  onPageChange?: (page: number) => void;
  renderSellerListingAction?: (listingId: string) => ReactNode;
};

type ConversationGroup = { key: string; label: string; conversations: ConversationInboxItem[] };

/** Participant-scoped inbox presentation; data, filtering and authorization stay with its caller. */
export function ConversationInbox({
  conversations,
  loading = false,
  loadError = false,
  onRefresh,
  onOpen,
  filters,
  onFiltersChange,
  page = 1,
  hasNextPage = false,
  onPageChange,
  renderSellerListingAction,
}: ConversationInboxProps) {
  const groups = useMemo(() => groupConversations(conversations), [conversations]);
  const [minimumRupees, setMinimumRupees] = useState('');
  const [maximumRupees, setMaximumRupees] = useState('');
  const [amountError, setAmountError] = useState('');
  const [draftOrigins, setDraftOrigins] = useState<string[]>(filters?.origin_id ?? []);
  const [draftPartners, setDraftPartners] = useState<string[]>(filters?.counterparty_user_id ?? []);

  useEffect(() => {
    setMinimumRupees(formatRupeesFilter(filters?.offer_min_paise));
    setMaximumRupees(formatRupeesFilter(filters?.offer_max_paise));
    setDraftOrigins(filters?.origin_id ?? []);
    setDraftPartners(filters?.counterparty_user_id ?? []);
    setAmountError('');
  }, [filters]);

  const updateFilters = (next: ConversationInboxFilters) => {
    setAmountError('');
    onFiltersChange?.(next);
  };
  const offerFiltersDisabled = filters?.origin_kind === 'wanted_request';
  const canFilter = Boolean(filters && onFiltersChange);

  function applyAmountFilters() {
    if (!filters || !onFiltersChange) return;
    const minimum = parseRupeesFilter(minimumRupees);
    const maximum = parseRupeesFilter(maximumRupees);
    if (minimum === null || maximum === null) {
      setAmountError('Enter whole, non-negative rupee amounts.');
      return;
    }
    if (minimum !== undefined && maximum !== undefined && minimum > maximum) {
      setAmountError('Minimum offer amount must not exceed the maximum.');
      return;
    }
    updateFilters({
      ...filters,
      offer_min_paise: offerFiltersDisabled ? undefined : minimum,
      offer_max_paise: offerFiltersDisabled ? undefined : maximum,
    });
  }

  function clearFilters() {
    setMinimumRupees('');
    setMaximumRupees('');
    setDraftOrigins([]);
    setDraftPartners([]);
    updateFilters({ view: 'all', sort: 'last_activity_desc' });
  }

  function applyIdentifierFilters() {
    if (!filters || !onFiltersChange) return;
    updateFilters({
      ...filters,
      origin_id: draftOrigins.length ? draftOrigins : undefined,
      counterparty_user_id: draftPartners.length ? draftPartners : undefined,
    });
  }

  function changeOriginKind(value: 'all' | 'sale_listing' | 'wanted_request') {
    if (!filters) return;
    const next: ConversationInboxFilters = {
      ...filters,
      origin_kind: value === 'all' ? undefined : value,
      origin_id: undefined,
    };
    if (value === 'wanted_request') {
      next.offer_status = undefined;
      next.offer_min_paise = undefined;
      next.offer_max_paise = undefined;
      if (next.sort === 'offer_amount_asc' || next.sort === 'offer_amount_desc') {
        next.sort = 'last_activity_desc';
      }
    }
    setMinimumRupees('');
    setMaximumRupees('');
    updateFilters(next);
  }

  const hasActiveFilters = Boolean(filters && (
    filters.view !== 'all' || filters.origin_kind || filters.origin_id?.length ||
    filters.counterparty_user_id?.length || filters.offer_status ||
    filters.offer_min_paise !== undefined || filters.offer_max_paise !== undefined
  ));

  return (
    <section aria-labelledby="conversation-inbox-title" className="conversation-inbox">
      <header className="conversation-inbox__header">
        <div>
          <h2 id="conversation-inbox-title">Your conversations</h2>
          <p>Private messages are encrypted on your device.</p>
        </div>
        <Button
          disabled={loading}
          onClick={() => void onRefresh().catch(() => undefined)}
          variant="secondary"
        >
          {loading ? 'Refreshing…' : 'Refresh'}
        </Button>
      </header>

      {canFilter && filters && onFiltersChange ? (
        <fieldset className="conversation-inbox__filters" disabled={loading}>
          <legend>Filter and sort conversations</legend>
          <div className="conversation-inbox__filter-grid">
            <label>
              Participation
              <select
                value={filters.view ?? 'all'}
                onChange={(event) => updateFilters({
                  ...filters,
                  view: event.currentTarget.value as NonNullable<ConversationListQuery['view']>,
                })}
              >
                <option value="all">All conversations</option>
                <option value="initiated">Buyer or responder · I started it</option>
                <option value="origin_owner">Seller or request author · It is mine</option>
              </select>
            </label>
            <label>
              Type
              <select
                value={filters.origin_kind ?? 'all'}
                onChange={(event) => changeOriginKind(
                  event.currentTarget.value as 'all' | 'sale_listing' | 'wanted_request',
                )}
              >
                <option value="all">Listings and requests</option>
                <option value="sale_listing">Sale listings</option>
                <option value="wanted_request">Wanted requests</option>
              </select>
            </label>
            <MultiChoiceDropdown
              disabled={loading}
              emptyLabel="All origins"
              label="Listing or request"
              onValuesChange={setDraftOrigins}
              options={originOptions(conversations, filters.origin_id ?? []).map((origin) => ({
                value: origin.id,
                label: origin.label,
              }))}
              values={draftOrigins}
            />
            <MultiChoiceDropdown
              disabled={loading}
              emptyLabel="All partners"
              label="Conversation partner"
              onValuesChange={setDraftPartners}
              options={partnerOptions(conversations, filters.counterparty_user_id ?? []).map((partner) => ({
                value: partner,
                label: `Partner · ${shortId(partner)}`,
              }))}
              values={draftPartners}
            />
            <label>
              Offer status
              <select
                disabled={offerFiltersDisabled}
                value={filters.offer_status ?? 'all'}
                onChange={(event) => updateFilters({
                  ...filters,
                  offer_status: event.currentTarget.value === 'all'
                    ? undefined
                    : event.currentTarget.value as 'submitted' | 'withdrawn',
                })}
              >
                <option value="all">Any offer status</option>
                <option value="submitted">Submitted</option>
                <option value="withdrawn">Withdrawn</option>
              </select>
            </label>
            <label>
              Sort by
              <select
                value={filters.sort ?? 'last_activity_desc'}
                onChange={(event) => updateFilters({
                  ...filters,
                  sort: event.currentTarget.value as NonNullable<ConversationListQuery['sort']>,
                })}
              >
                <option value="last_activity_desc">Most recent activity</option>
                <option value="offer_amount_asc" disabled={offerFiltersDisabled}>Offer amount: low to high</option>
                <option value="offer_amount_desc" disabled={offerFiltersDisabled}>Offer amount: high to low</option>
              </select>
            </label>
            <label>
              Minimum offer (₹)
              <input
                disabled={offerFiltersDisabled}
                inputMode="numeric"
                min="0"
                onChange={(event) => setMinimumRupees(event.currentTarget.value)}
                step="1"
                type="number"
                value={minimumRupees}
              />
            </label>
            <label>
              Maximum offer (₹)
              <input
                disabled={offerFiltersDisabled}
                inputMode="numeric"
                min="0"
                onChange={(event) => setMaximumRupees(event.currentTarget.value)}
                step="1"
                type="number"
                value={maximumRupees}
              />
            </label>
          </div>
          <div className="conversation-inbox__filter-actions">
            <Button onClick={applyIdentifierFilters} variant="secondary">
              Apply origin and partner filters
            </Button>
            <Button disabled={offerFiltersDisabled} onClick={applyAmountFilters} variant="secondary">
              Apply amount range
            </Button>
            <Button onClick={clearFilters} variant="secondary">Clear filters</Button>
          </div>
          <p className="conversation-inbox__filter-help">
            Offer filters apply to Sale Listings and exclude conversations without an offer. Amount sorting keeps no-offer conversations last.
            Origin and partner choices come from the conversations currently loaded; select several, apply them together, or use pagination to find other IDs.
            {offerFiltersDisabled ? ' Select Sale listings or All to enable offer filters.' : ''}
          </p>
          {amountError ? <p className="conversation-inbox__notice" role="alert">{amountError}</p> : null}
        </fieldset>
      ) : null}

      {loadError ? (
        <p className="conversation-inbox__notice" role="status">
          Couldn’t load conversations. Try refreshing.
        </p>
      ) : null}
      {loading && conversations.length === 0 ? (
        <p role="status">Loading conversations…</p>
      ) : conversations.length === 0 ? (
        <p className="conversation-inbox__empty">
          {hasActiveFilters ? 'No conversations match these filters.' : 'No conversations yet.'}
        </p>
      ) : (
        <div className="conversation-inbox__groups">
          <p className="conversation-inbox__page-note">
            Each group shows only conversations on this page; use pagination to see more.
          </p>
          {groups.map((group) => (
            <section aria-label={group.label} className="conversation-inbox__group" key={group.key}>
              <header className="conversation-inbox__group-header">
                <h3>{group.label}</h3>
                {group.conversations.some((item) => item.role === 'seller' && item.origin_kind === 'sale_listing') &&
                  group.conversations[0].origin_id && renderSellerListingAction?.(group.conversations[0].origin_id)}
                <span>{group.conversations.length} {group.conversations.length === 1 ? 'conversation' : 'conversations'} on this page</span>
              </header>
              <ul className="conversation-inbox__list">
                {group.conversations.map((conversation) => (
                  <li key={conversation.conversation_id}>
                    <Button
                      aria-label={`Open ${conversation.label}`}
                      className="conversation-inbox__item"
                      onClick={() => onOpen(conversation.conversation_id)}
                      variant="secondary"
                    >
                      <span className="conversation-inbox__item-copy">
                        <span className="conversation-inbox__label">Conversation · {shortId(conversation.conversation_id)}</span>
                        <span className="conversation-inbox__meta">
                          {conversation.role} · {conversation.counterparty_user_id ? `Partner ${shortId(conversation.counterparty_user_id)} · ` : ''}
                          {formatActivityTime(conversation.last_activity_at)}
                        </span>
                        {conversation.current_offer ? (
                          <span className="conversation-inbox__offer">
                            {formatOffer(conversation.current_offer.amount_paise)} · {conversation.current_offer.status}
                          </span>
                        ) : null}
                      </span>
                      {conversation.unread_count > 0 ? (
                        <span className="conversation-inbox__unread">
                          <span aria-hidden="true">{conversation.unread_count}</span>
                          <span className="conversation-inbox__sr-only">
                            {conversation.unread_count} unread
                          </span>
                        </span>
                      ) : null}
                    </Button>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
      {onPageChange ? (
        <nav aria-label="Conversation pages" className="conversation-inbox__pagination">
          <Button disabled={loading || page <= 1} onClick={() => onPageChange(page - 1)} variant="secondary">Previous</Button>
          <span>Page {page}</span>
          <Button disabled={loading || !hasNextPage} onClick={() => onPageChange(page + 1)} variant="secondary">Next</Button>
        </nav>
      ) : null}
    </section>
  );
}

function groupConversations(items: ConversationInboxItem[]): ConversationGroup[] {
  const groups = new Map<string, ConversationGroup>();
  for (const item of items) {
    const groupKey = item.origin_kind && item.origin_id
      ? `${item.origin_kind}:${item.origin_id}`
      : `label:${item.label}`;
    const label = item.origin_kind && item.origin_id
      ? `${item.origin_kind === 'sale_listing' ? 'Sale listing' : 'Wanted request'} · ${shortId(item.origin_id)}`
      : item.label;
    const group = groups.get(groupKey) ?? { key: groupKey, label, conversations: [] };
    group.conversations.push(item);
    groups.set(groupKey, group);
  }
  return [...groups.values()];
}

function originOptions(items: ConversationInboxItem[], selectedIds: readonly string[]): { id: string; label: string }[] {
  const origins = new Map<string, 'sale_listing' | 'wanted_request' | 'origin'>();
  for (const item of items) {
    if (item.origin_id && item.origin_kind) origins.set(item.origin_id, item.origin_kind);
  }
  for (const selectedId of selectedIds) {
    if (!origins.has(selectedId)) origins.set(selectedId, 'origin');
  }
  return [...origins].sort(([left], [right]) => left.localeCompare(right)).map(([id, kind]) => ({
    id,
    label: `${kind === 'sale_listing' ? 'Sale listing' : kind === 'wanted_request' ? 'Wanted request' : 'Origin'} · ${shortId(id)}`,
  }));
}

function partnerOptions(items: ConversationInboxItem[], selectedIds: readonly string[]): string[] {
  const partners = new Set(items.flatMap((item) => item.counterparty_user_id ? [item.counterparty_user_id] : []));
  for (const selectedId of selectedIds) partners.add(selectedId);
  return [...partners].sort();
}

function parseRupeesFilter(value: string): number | undefined | null {
  if (value.trim() === '') return undefined;
  if (!/^\d+$/.test(value)) return null;
  const rupees = Number(value);
  return Number.isSafeInteger(rupees) && rupees <= Math.floor(Number.MAX_SAFE_INTEGER / 100)
    ? rupees * 100
    : null;
}

function formatRupeesFilter(paise?: number | null): string {
  return paise === undefined || paise === null ? '' : String(paise / 100);
}

function shortId(value: string): string {
  return value.length > 16 ? `${value.slice(0, 8)}…${value.slice(-4)}` : value;
}

function formatOffer(paise: number): string {
  const amount = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(paise / 100);
  return `₹${amount}`;
}

function formatActivityTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'recent activity' : date.toLocaleString();
}
