import { useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { Button } from '../../shared/ui';
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
  group_has_more?: boolean;
  group_unread_count?: number;
  counterparty_handle?: string | null;
  counterparty_account_class?: "regular" | "temporary" | null;
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
  onLoadMoreGroup?: (item: ConversationInboxItem) => void;
  renderSellerListingAction?: (listingId: string) => ReactNode;
  renderOriginContext?: (kind: 'sale_listing' | 'wanted_request', originId: string) => ReactNode;
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
  onLoadMoreGroup,
  renderOriginContext,
}: ConversationInboxProps) {
  const groups = useMemo(() => groupConversations(conversations, filters?.group_by), [conversations, filters?.group_by]);
  const [visibleCounts, setVisibleCounts] = useState<Record<string, number>>({});
  const [hiddenGroups, setHiddenGroups] = useState<Record<string, boolean>>({});
  const canFilter = Boolean(filters && onFiltersChange);

  function changeFilters(next: ConversationInboxFilters) {
    setVisibleCounts({});
    setHiddenGroups({});
    onFiltersChange?.(next);
  }

  function clearFilters() {
    if (!filters) return;
    changeFilters({ view: 'all', sort: 'last_activity_desc', marketplace_mode: 'all', group_by: 'item' });
  }

  const hasActiveFilters = Boolean(filters && (
    (filters.view !== undefined && filters.view !== 'all') || (filters.sort !== undefined && filters.sort !== 'last_activity_desc') || filters.origin_kind || filters.origin_id?.length ||
    filters.counterparty_user_id?.length || filters.offer_status || filters.offer_min_paise !== undefined || filters.offer_max_paise !== undefined
  ));

  return (
    <section aria-labelledby="conversation-inbox-title" className="conversation-inbox">
      <header className="conversation-inbox__header">
        <div>
          <h2 id="conversation-inbox-title">Inbox</h2>
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

      {canFilter && <div className="conversation-inbox__controls">
        <fieldset className="conversation-inbox__mode-set">
          <legend>View</legend>
          {(['all', 'buying', 'selling'] as const).map((mode) => <Button key={mode} variant={filters?.marketplace_mode === mode ? 'primary' : 'secondary'}
            aria-pressed={(filters?.marketplace_mode ?? 'all') === mode} onClick={() => changeFilters({ view: 'all', sort: 'last_activity_desc', group_by: filters?.group_by ?? 'item', marketplace_mode: mode })}>{mode === 'all' ? 'All' : mode === 'buying' ? 'Buying' : 'Selling'}</Button>)}
        </fieldset>
        <fieldset className="conversation-inbox__mode-set">
          <legend>Group by</legend>
          {(['item', 'person'] as const).map((grouping) => <Button key={grouping} variant={filters?.group_by === grouping ? 'primary' : 'secondary'}
            aria-pressed={(filters?.group_by ?? 'item') === grouping} onClick={() => changeFilters({ ...filters, group_by: grouping })}>{grouping === 'item' ? 'Item' : 'Person'}</Button>)}
        </fieldset>
      </div>}
      {canFilter && hasActiveFilters ? (
        <details className="conversation-inbox__sort-filter">
          <summary>Sort &amp; Filter</summary>
          <p>Conversations are ordered by recent activity. Offer and participant filters are hidden while this inbox is organized by listing or request.</p>
          {hasActiveFilters && <Button disabled={loading} onClick={clearFilters} variant="secondary">Clear saved filters</Button>}
        </details>
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
            Most recent activity first.
          </p>
          {groups.map((group) => (
            <section aria-label={group.label} className="conversation-inbox__group" key={group.key}>
              {(() => {
                const hidden = hiddenGroups[group.key] ?? true;
                const visibleCount = visibleCounts[group.key] ?? 5;
                const visibleConversations = hidden ? [] : group.conversations.slice(0, visibleCount);
                const canShowMore = !hidden && (visibleCount < group.conversations.length || Boolean(group.conversations[0]?.group_has_more));
                const unreadCount = group.conversations[0]?.group_unread_count ?? 0;
                return <>
              <header className="conversation-inbox__group-header">
                <div className="conversation-inbox__heading">
                  <h3>{group.label}</h3>
                  {unreadCount > 0 && <span className="conversation-inbox__group-unread">
                    <span className="conversation-inbox__sr-only">{unreadCount} unread messages</span>
                    <span aria-hidden="true">{unreadCount} unread</span>
                  </span>}
                </div>
                {filters?.group_by !== "person" && group.conversations[0].origin_kind && group.conversations[0].origin_id
                  ? renderOriginContext?.(group.conversations[0].origin_kind, group.conversations[0].origin_id)
                  : null}
                {filters?.group_by !== "person" && group.conversations[0].origin_id ? <Link className="ui-button ui-button--secondary conversation-inbox__origin-link" to={`${group.conversations[0].origin_kind === 'sale_listing' ? '/listings/' : '/wanted/'}${encodeURIComponent(group.conversations[0].origin_id)}`}>Open {group.conversations[0].origin_kind === 'sale_listing' ? 'listing' : 'Wanted Request'}</Link> : null}
                <div className="conversation-inbox__group-actions">
                {filters?.group_by !== 'person' && group.conversations.some((item) => item.role === 'seller' && item.origin_kind === 'sale_listing') &&
                  group.conversations[0].origin_id && <div className="conversation-inbox__seller-action">{renderSellerListingAction?.(group.conversations[0].origin_id)}</div>}
                <span className="conversation-inbox__group-count">{group.conversations.length}{group.conversations.some((item) => item.group_has_more) ? '+' : ''} conversations</span>
                <Button variant="secondary" aria-expanded={!hidden} onClick={() => {
                  setHiddenGroups((current) => ({ ...current, [group.key]: !hidden }));
                  if (hidden) setVisibleCounts((current) => ({ ...current, [group.key]: 5 }));
                }}>{hidden ? 'Show conversations' : 'Hide conversations'}</Button>
                </div>
              </header>
              {!hidden && <ul className="conversation-inbox__list">
                {visibleConversations.map((conversation) => (
                  <li key={conversation.conversation_id}>
                    {filters?.group_by === "person" && conversation.origin_id && conversation.origin_kind && <div className="conversation-inbox__person-origin">
                      {renderOriginContext?.(conversation.origin_kind, conversation.origin_id)}
                      <Link className="ui-button ui-button--secondary" to={`${conversation.origin_kind === 'sale_listing' ? '/listings/' : '/wanted/'}${conversation.origin_id}`}>Open {conversation.origin_kind === 'sale_listing' ? 'listing' : 'Wanted Request'}</Link>
                      {conversation.role === 'seller' && conversation.origin_kind === 'sale_listing' && renderSellerListingAction?.(conversation.origin_id)}
                    </div>}
                    <Button
                      aria-label={`Open ${conversation.role} conversation`}
                      className="conversation-inbox__item"
                      onClick={() => onOpen(conversation.conversation_id)}
                      variant="secondary"
                    >
                      <span className="conversation-inbox__item-copy">
                        <span className="conversation-inbox__label">{conversation.counterparty_handle ? `@${conversation.counterparty_handle}` : "Member completing setup"}</span>
                        {conversation.counterparty_account_class === "temporary" && <span className="conversation-inbox__meta">Temporary account</span>}
                        <span className="conversation-inbox__meta">
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
              </ul>}
              {canShowMore && <Button variant="secondary" onClick={async () => {
                if (visibleCount >= group.conversations.length && onLoadMoreGroup) await onLoadMoreGroup(group.conversations[0]);
                setVisibleCounts((current) => ({ ...current, [group.key]: visibleCount + 5 }));
              }}>Show 5 more conversations</Button>}
                </>;
              })()}
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

function groupConversations(items: ConversationInboxItem[], grouping?: "item" | "person" | null): ConversationGroup[] {
  const groups = new Map<string, ConversationGroup>();
  for (const item of items) {
    const groupKey = grouping === "person" ? `person:${item.counterparty_user_id}` : item.origin_kind && item.origin_id
      ? `${item.origin_kind}:${item.origin_id}`
      : `label:${item.label}`;
    const label = grouping === "person" ? (item.counterparty_handle ? `@${item.counterparty_handle}` : "Member completing setup") : item.origin_kind && item.origin_id
      ? item.origin_kind === 'sale_listing' ? 'Sale listing' : 'Wanted request'
      : item.label;
    const group = groups.get(groupKey) ?? { key: groupKey, label, conversations: [] };
    group.conversations.push(item);
    groups.set(groupKey, group);
  }
  return [...groups.values()];
}

function formatOffer(paise: number): string {
  const amount = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(paise / 100);
  return `₹${amount}`;
}

function formatActivityTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'recent activity' : date.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });
}
