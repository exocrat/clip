import { describe, expect, it, vi } from 'vitest';
import { ConversationApi, ConversationApiError } from '../src/features/conversations';
import type { MessageRequest } from '../../../contracts/generated/types.gen';

const thread = '00000000-0000-4000-8000-000000000001';
const alice = '00000000-0000-4000-8000-000000000002';
const bob = '00000000-0000-4000-8000-000000000003';
const operation = '00000000-0000-4000-8000-000000000004';
const envelope = {
  protocol_id: 'open-e2ee-signal', protocol_version: '13.0.0', envelope_version: 1,
  sdk_message_type: 'ciphertext', sender_key_version: 1, recipient_key_version: 1,
  client_timestamp_ms: 1, payload_base64: btoa('opaque synthetic bytes'),
} as const;
const entry = {
  entry_id: operation, sequence: 1, kind: 'message', sender_user_id: bob,
  created_at: '2026-10-23T00:00:00.000000Z', envelope, content_deleted: false,
};
const summary = {
  conversation_id: thread, origin_kind: 'sale_listing', origin_id: operation,
  initiator_user_id: alice, caller_role: 'initiator', counterparty_user_id: bob,
  last_activity_at: '2026-10-23T00:00:00.000000Z', own_last_read_sequence: 0,
  unread_count: 1, current_offer: null,
};

/** Test-only HTTP double. Production must supply Identity's authenticated transport. */
function setup(value: unknown, status = 200) {
  const transport = vi.fn(async (_path: string, _init: RequestInit) =>
    new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } }));
  return { transport, api: new ConversationApi(transport) };
}

describe('ConversationApi', () => {
  it('maps authorized inbox filters and abort signals without adding authentication assumptions', async () => {
    const page = { items: [summary], page: 1, page_size: 20, has_next: false };
    const { api, transport } = setup(page);
    const controller = new AbortController();
    expect(await api.listMine({ view: 'initiated', origin_id: null, page: 1 }, controller.signal)).toEqual(page);
    expect(transport).toHaveBeenCalledWith('/conversations?view=initiated&page=1', expect.objectContaining({
      method: 'GET', signal: controller.signal, cache: 'no-store', redirect: 'error',
    }));
    const init = transport.mock.calls[0][1];
    expect(init).not.toHaveProperty('credentials');
    expect(init.headers).not.toHaveProperty('Authorization');
    expect(init.headers).not.toHaveProperty('X-User-ID');
  });

  it('binds summary responses to the requested conversation', async () => {
    expect(await setup(summary).api.readSummary(thread)).toEqual(summary);
    await expect(setup({ ...summary, conversation_id: operation }).api.readSummary(thread))
      .rejects.toMatchObject({ kind: 'invalid_response' });
    expect(() => setup(summary).api.readSummary('../other')).toThrow(ConversationApiError);
  });

  it('accepts empty pages that scan hidden controls and rejects stalled pagination or reordering', async () => {
    const hidden = { items: [], scanned_through_sequence: 2, has_more: true };
    expect(await setup(hidden).api.readEntries(thread, 1)).toEqual(hidden);
    expect(await setup({ items: [], scanned_through_sequence: 1, has_more: false }).api.readEntries(thread, 1))
      .toEqual({ items: [], scanned_through_sequence: 1, has_more: false });
    for (const value of [
      { ...hidden, scanned_through_sequence: 1 },
      { ...hidden, scanned_through_sequence: 0, has_more: false },
      { items: [entry, entry], scanned_through_sequence: 1, has_more: false },
      { items: [{ ...entry, sequence: 4 }], scanned_through_sequence: 2, has_more: false },
    ]) {
      await expect(setup(value).api.readEntries(thread, value.items.length ? 0 : 1))
        .rejects.toMatchObject({ kind: 'invalid_response' });
    }
  });

  it('never acknowledges reads as a side effect of fetching entries', async () => {
    const { api, transport } = setup({ items: [entry], scanned_through_sequence: 1, has_more: false });
    await api.readEntries(thread);
    expect(transport).toHaveBeenCalledTimes(1);
    expect(transport.mock.calls[0][0]).toBe(`/conversations/${thread}/entries?after_sequence=0`);
    const ack = setup({ own_last_read_sequence: 1 });
    await ack.api.acknowledgeDisplayed(thread, 1);
    expect(ack.transport.mock.calls[0][1]).toMatchObject({ method: 'PUT', body: '{"last_read_sequence":1}' });
    await expect(setup({ own_last_read_sequence: 0 }).api.acknowledgeDisplayed(thread, 1))
      .rejects.toMatchObject({ kind: 'invalid_response' });
  });

  it('sends only the prepared ciphertext and never automatically retries an ambiguous write', async () => {
    const { api, transport } = setup(entry);
    const request: MessageRequest = { operation_id: operation, envelope };
    await api.submitMessage(thread, request);
    expect(transport.mock.calls[0][1]).toMatchObject({ method: 'POST', body: JSON.stringify(request) });
    const failing = vi.fn(async () => { throw new Error('synthetic private diagnostics'); });
    const retryApi = new ConversationApi(failing);
    await expect(retryApi.submitMessage(thread, request)).rejects.toMatchObject({ kind: 'transport' });
    expect(failing).toHaveBeenCalledTimes(1);
    await expect(retryApi.submitMessage(thread, request)).rejects.toBeInstanceOf(ConversationApiError);
    expect(failing).toHaveBeenCalledTimes(2);
    await expect(setup({ ...entry, envelope: { ...envelope, payload_base64: btoa('different') } }).api.submitMessage(thread, request))
      .rejects.toMatchObject({ kind: 'invalid_response' });
  });

  it.each([401, 403, 404, 409, 422, 429, 503])('retains safe status %i without error-body content', async (status) => {
    const { api, transport } = setup({ error: { message: 'synthetic private diagnostics' } }, status);
    const error = await api.readSummary(thread).catch((failure: unknown) => failure);
    expect(error).toBeInstanceOf(ConversationApiError);
    expect(error).toMatchObject({ status, kind: 'http' });
    expect(String(error)).not.toContain('private diagnostics');
    expect(error).not.toHaveProperty('cause');
    expect(transport).toHaveBeenCalledTimes(1);
  });

  it('rejects malformed/HTML success responses and malformed encrypted content', async () => {
    const html = new ConversationApi(async () => new Response('<html>sign in</html>', { headers: { 'Content-Type': 'text/html' } }));
    await expect(html.readSummary(thread)).rejects.toMatchObject({ kind: 'invalid_response' });
    for (const value of [null, {}, { ...summary, unread_count: '1' }, { ...summary, last_activity_at: 'invalid' }]) {
      await expect(setup(value).api.readSummary(thread)).rejects.toMatchObject({ kind: 'invalid_response' });
    }
    for (const change of [
      { sdk_message_type: 'retry_request' }, { payload_base64: 'not base64' },
      { recipient_key_version: 0 }, { protocol_version: 'unsupported' },
    ]) {
      await expect(setup({ items: [{ ...entry, envelope: { ...envelope, ...change } }], scanned_through_sequence: 1, has_more: false })
        .api.readEntries(thread)).rejects.toMatchObject({ kind: 'invalid_response' });
    }
  });

  it('rejects malformed public-key bundles and mismatched prekey inventory versions', async () => {
    expect(await setup(null).api.readOwnKey()).toBeNull();
    await expect(setup({}, 503).api.readOwnKey()).rejects.toMatchObject({ kind: 'http', status: 503 });
    await expect(setup({}, 401).api.readOwnKey()).rejects.toMatchObject({ kind: 'http', status: 401 });
    await expect(setup({ user_id: alice }).api.readOwnKey()).rejects.toMatchObject({ kind: 'invalid_response' });
    await expect(setup({ members: [{ user_id: alice }, { user_id: bob }] }).api.readMemberKeys(thread))
      .rejects.toMatchObject({ kind: 'invalid_response' });
    expect(await setup({ key_version: 1, ec_one_time_count: 0, kem_one_time_count: 0 }).api.readOwnInventory())
      .toEqual({ key_version: 1, ec_one_time_count: 0, kem_one_time_count: 0 });
    await expect(setup({ key_version: 2, ec_one_time_count: 0, kem_one_time_count: 0 }).api.publishOwnPrekeys({
      key_version: 1, operation_id: operation,
      prekeys: [{ key_type: 'ecPreKey', key_id: 1, public_key_base64: btoa('p'.repeat(32)) }],
    })).rejects.toMatchObject({ kind: 'invalid_response' });
  });

  it('maps public registration, member lookup, publication and reservation to the reviewed routes', async () => {
    const material = {
      protocol_id: 'open-e2ee-signal', protocol_version: '13.0.0', registration_id: 1, device_id: 1 as const,
      identity: { version: 1 as const, x25519_public_key_base64: btoa('x'.repeat(32)), ed25519_public_key_base64: btoa('e'.repeat(32)) },
      ec_signed_prekey: { key_id: 1, public_key_base64: btoa('p'.repeat(32)), signature_base64: btoa('s'.repeat(64)) },
      kem_last_resort_prekey: { key_id: 2, public_key_base64: btoa('k'.repeat(1569)), signature_base64: btoa('s'.repeat(64)) },
    };
    const key = { ...material, user_id: bob, key_version: 1 };
    const ownRead = setup(key);
    expect(await ownRead.api.readOwnKey()).toEqual(key);
    expect(ownRead.transport.mock.calls[0][0]).toBe('/me/conversation-key');
    expect(ownRead.transport.mock.calls[0][1].method).toBe('GET');
    const own = setup({ user_id: alice, key_version: 1, protocol_id: material.protocol_id, protocol_version: material.protocol_version });
    await own.api.registerOwnKey({ ...material, operation_id: operation });
    expect(own.transport.mock.calls[0][0]).toBe('/me/conversation-key');
    expect(own.transport.mock.calls[0][1].method).toBe('PUT');
    const members = { members: [key, { ...key, user_id: alice }] };
    expect(await setup(members).api.readMemberKeys(thread)).toEqual(members);
    const reservation = { key_bundle: key, registration_id: 1, device_id: 1, ec_one_time_prekey: null, kem_one_time_prekey: null };
    const consume = setup(reservation);
    expect(await consume.api.consumeMemberPrekeys(thread, { operation_id: operation })).toEqual(reservation);
    expect(consume.transport.mock.calls[0]).toEqual([
      `/conversations/${thread}/prekey-bundle`, expect.objectContaining({ method: 'POST', body: JSON.stringify({ operation_id: operation }) }),
    ]);
    await expect(setup({ ...reservation, registration_id: 2 }).api.consumeMemberPrekeys(thread, { operation_id: operation }))
      .rejects.toMatchObject({ kind: 'invalid_response' });
    const publish = setup({ key_version: 1, ec_one_time_count: 1, kem_one_time_count: 0 });
    await publish.api.publishOwnPrekeys({ key_version: 1, operation_id: operation, prekeys: [
      { key_type: 'ecPreKey', key_id: 3, public_key_base64: btoa('p'.repeat(32)) },
    ] });
    expect(publish.transport.mock.calls[0][0]).toBe('/me/conversation-prekeys');
    expect(publish.transport.mock.calls[0][1].method).toBe('POST');
  });
});
