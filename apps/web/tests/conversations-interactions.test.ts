// @vitest-environment jsdom
import { act, createElement } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ConversationThread, type ConversationThreadProps } from '../src/features/conversations/ConversationThread';
import { ConversationDetailPage, ConversationInboxPage, ConversationPageRuntimeProvider,
  type ConversationPageRuntime } from '../src/features/conversations/ConversationPages';
import { openIndexedDbConversationSession } from '../src/features/conversations/relay';
import type { ConversationApi } from '../src/features/conversations/api';

// Isolate page lifecycle from crypto/IndexedDB. Real SDK and PostgreSQL behavior
// have separate suites; these fixtures prove React visibility and account isolation.
vi.mock('../src/features/conversations/relay', () => ({ openIndexedDbConversationSession: vi.fn() }));

/** Supply controlled browser intersection events without pretending jsdom does layout. */
class Observer {
  static instances: Observer[] = [];
  targets: Element[] = [];
  disconnect = vi.fn();
  constructor(private callback: IntersectionObserverCallback) { Observer.instances.push(this); }
  observe(target: Element) { this.targets.push(target); }
  emit(target: Element, isIntersecting = true, intersectionRatio = isIntersecting ? 1 : 0) {
    this.callback([{ target, isIntersecting, intersectionRatio } as IntersectionObserverEntry], this as unknown as IntersectionObserver);
  }
}

function latestObserver(): Observer {
  const observer = Observer.instances.at(-1);
  if (!observer) throw new Error('Expected a mounted message observer');
  return observer;
}

let host: HTMLDivElement;
let root: Root;
beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  vi.stubGlobal('IntersectionObserver', Observer);
  Observer.instances = [];
  vi.mocked(openIndexedDbConversationSession).mockReset();
  host = document.createElement('div');
  document.body.append(host);
  root = createRoot(host);
});
afterEach(async () => {
  await act(async () => root.unmount());
  host.remove();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function props(): ConversationThreadProps {
  return { current_user_id: 'alice', key_state: { kind: 'ready' }, last_read_sequence: 0,
    entries: [1, 2].map((sequence) => ({ entry_id: `entry-${sequence}`, sequence,
      sender_user_id: 'bob', created_at: '2026-10-25T00:00:00Z', text: `Synthetic ${sequence}`, content_deleted: false })),
    onRefresh: vi.fn(async () => undefined), onSend: vi.fn(async () => undefined),
    onRetry: vi.fn(async () => undefined), onAcknowledgeDisplayed: vi.fn(async () => undefined) };
}

describe('conversation display acknowledgements', () => {
  it('acknowledges intersecting messages only, never fetching or offscreen rows', async () => {
    const view = props();
    await act(async () => root.render(createElement(ConversationThread, view)));
    expect(view.onRefresh).toHaveBeenCalledOnce();
    expect(view.onAcknowledgeDisplayed).not.toHaveBeenCalled();
    const observer = latestObserver();
    await act(async () => observer.emit(observer.targets[0], false));
    expect(view.onAcknowledgeDisplayed).not.toHaveBeenCalled();
    await act(async () => observer.emit(observer.targets[0], true, 0.1));
    expect(view.onAcknowledgeDisplayed).not.toHaveBeenCalled();
    await act(async () => observer.emit(observer.targets[0]));
    await act(async () => observer.emit(observer.targets[0]));
    expect(view.onAcknowledgeDisplayed).toHaveBeenCalledTimes(1);
    await act(async () => observer.emit(observer.targets[1]));
    expect(vi.mocked(view.onAcknowledgeDisplayed).mock.calls).toEqual([[1], [2]]);
  });

  it('retries a failed visible acknowledgement without accepting it as committed', async () => {
    const view = props();
    vi.mocked(view.onAcknowledgeDisplayed).mockRejectedValueOnce(new Error('Synthetic failure'));
    await act(async () => root.render(createElement(ConversationThread, view)));
    const observer = latestObserver();
    await act(async () => observer.emit(observer.targets[0]));
    await act(async () => observer.emit(observer.targets[0]));
    await act(async () => observer.emit(observer.targets[0]));
    expect(vi.mocked(view.onAcknowledgeDisplayed).mock.calls).toEqual([[1], [1]]);
  });

  it('does not acknowledge intersections while the browser document is hidden', async () => {
    const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden');
    const view = props();
    await act(async () => root.render(createElement(ConversationThread, view)));
    const observer = latestObserver();
    await act(async () => observer.emit(observer.targets[0]));
    expect(view.onAcknowledgeDisplayed).not.toHaveBeenCalled();
    visibility.mockReturnValue('visible');
    await act(async () => observer.emit(observer.targets[0]));
    expect(view.onAcknowledgeDisplayed).toHaveBeenCalledWith(1);
  });
});

/** Only the fields read by the page are provided; this is no API/key validation test. */
function runtime(userId: string, summary: () => Promise<unknown>): ConversationPageRuntime {
  return { userId, api: { readSummary: vi.fn(summary),
    readOwnKey: vi.fn(async () => ({ key_version: 1 })),
    readMemberKeys: vi.fn(async () => ({ members: [{ user_id: 'bob', key_version: 1 }] })),
    readState: vi.fn(async () => ({ own_last_read_sequence: 0 })),
    readEntries: vi.fn(async () => ({ items: [{ entry_id: 'sent', sequence: 1, sender_user_id: userId,
      kind: 'message', created_at: '2026-10-25T00:00:00Z', content_deleted: false, envelope: null }],
      scanned_through_sequence: 1, has_more: false })),
    listMine: vi.fn(async () => ({ items: [{ conversation_id: 'thread', initiator_user_id: userId,
      counterparty_user_id: 'bob', origin_kind: 'sale_listing', unread_count: 1 }], has_next: false })),
  } as unknown as ConversationApi };
}

function detail(value: ConversationPageRuntime | null) {
  return createElement(MemoryRouter, {}, createElement(ConversationPageRuntimeProvider, { runtime: value },
    createElement(ConversationDetailPage, { conversationId: 'thread' })));
}

describe('conversation account lifecycle', () => {
  it('clears decrypted messages on account change and discards late polling results', async () => {
    const stop = vi.fn(async () => undefined);
    vi.mocked(openIndexedDbConversationSession).mockResolvedValue({ stop,
      crypto: { resumeParticipantSession: vi.fn(async () => true) },
      history: { read: vi.fn(async () => ({ received: [], sent: [{ request: { text: 'Alice private fixture' },
        confirmation: { message_id: 'sent' } }] })) },
    } as unknown as Awaited<ReturnType<typeof openIndexedDbConversationSession>>);
    const alice = runtime('alice', async () => ({ conversation_id: 'thread', origin_kind: 'sale_listing',
      initiator_user_id: 'alice', counterparty_user_id: 'bob' }));
    await act(async () => root.render(detail(alice)));
    expect(host.textContent).toContain('Alice private fixture');
    let finishPoll!: (value: unknown) => void;
    vi.mocked(alice.api.readEntries).mockImplementationOnce(() => new Promise((resolve) => {
      finishPoll = resolve as (value: unknown) => void;
    }));
    await act(async () => { window.dispatchEvent(new Event('focus')); });
    const carol = runtime('carol', () => new Promise(() => undefined));
    await act(async () => root.render(detail(carol)));
    expect(host.textContent).not.toContain('Alice private fixture');
    expect(stop).toHaveBeenCalled();
    await act(async () => finishPoll({ items: [], scanned_through_sequence: 1, has_more: false }));
    expect(host.textContent).not.toContain('Alice private fixture');
  });

  it('clears prior-account inbox rows while the next account loads', async () => {
    const alice = runtime('alice', async () => null);
    const view = (value: ConversationPageRuntime) => createElement(MemoryRouter, {},
      createElement(ConversationPageRuntimeProvider, { runtime: value }, createElement(ConversationInboxPage)));
    await act(async () => root.render(view(alice)));
    expect(host.querySelectorAll('.conversation-inbox__item')).toHaveLength(1);
    const carol = runtime('carol', async () => null);
    vi.mocked(carol.api.listMine).mockImplementation(() => new Promise(() => undefined));
    await act(async () => root.render(view(carol)));
    expect(host.textContent).not.toContain('1 unread');
  });

  it('closes the active session on logout and ignores its late reads', async () => {
    const stop = vi.fn(async () => undefined);
    const historyRead = vi.fn(async () => ({ received: [], sent: [{ request: { text: 'Logout private fixture' },
      confirmation: { message_id: 'sent' } }] }));
    vi.mocked(openIndexedDbConversationSession).mockResolvedValue({ stop,
      crypto: { resumeParticipantSession: vi.fn(async () => true) },
      history: { read: historyRead },
    } as unknown as Awaited<ReturnType<typeof openIndexedDbConversationSession>>);
    const alice = runtime('alice', async () => ({ conversation_id: 'thread', origin_kind: 'sale_listing',
      initiator_user_id: 'alice', counterparty_user_id: 'bob' }));
    await act(async () => root.render(detail(alice)));
    expect(host.textContent).toContain('Logout private fixture');
    let finishPoll!: (value: unknown) => void;
    vi.mocked(alice.api.readEntries).mockImplementationOnce(() => new Promise((resolve) => {
      finishPoll = resolve as (value: unknown) => void;
    }));
    await act(async () => { window.dispatchEvent(new Event('focus')); });
    await act(async () => root.render(detail(null)));
    expect(stop).toHaveBeenCalledOnce();
    expect(host.textContent).toContain('Sign in to view this conversation');
    expect(host.textContent).not.toContain('Logout private fixture');
    const readsBeforeResponse = historyRead.mock.calls.length;
    await act(async () => finishPoll({ items: [], scanned_through_sequence: 1, has_more: false }));
    expect(historyRead).toHaveBeenCalledTimes(readsBeforeResponse);
    expect(host.textContent).toContain('Sign in to view this conversation');
    expect(host.textContent).not.toContain('Logout private fixture');
    expect(Observer.instances.at(-1)?.disconnect).toHaveBeenCalled();
  });
});
