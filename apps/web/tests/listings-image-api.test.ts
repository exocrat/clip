import { withCsrf } from './helpers/csrf';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ListingsApiError, uploadListingImage } from '../src/features/listings/listingsApi';

type Intent = {
  upload_id: string;
  upload_url: string;
  required_headers: Record<string, string>;
  url_expires_at: string;
};

const uploadId = '10000000-0000-4000-8000-000000000001';
const operationId = '20000000-0000-4000-8000-000000000002';
const fileBytes = new File(['synthetic image bytes'], 'photo.png', { type: 'image/png' });

function intent(url = 'https://private-storage.invalid/first-token'): Intent {
  return {
    upload_id: uploadId,
    upload_url: url,
    required_headers: { 'Content-Type': 'image/png', 'If-None-Match': '*' },
    url_expires_at: '2026-10-22T12:05:00Z',
  };
}

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

class FakeXMLHttpRequest {
  static statuses: number[] = [];
  static requests: FakeXMLHttpRequest[] = [];
  readonly upload = {} as XMLHttpRequestUpload;
  status = 0;
  timeout = 0;
  onload: XMLHttpRequest['onload'] = null;
  onerror: XMLHttpRequest['onerror'] = null;
  ontimeout: XMLHttpRequest['ontimeout'] = null;
  onabort: XMLHttpRequest['onabort'] = null;
  onloadend: XMLHttpRequest['onloadend'] = null;
  method = '';
  url = '';
  body: XMLHttpRequestBodyInit | null = null;
  headers: Record<string, string> = {};

  open(method: string, url: string) {
    this.method = method;
    this.url = url;
  }

  setRequestHeader(name: string, value: string) {
    this.headers[name] = value;
  }

  send(body: XMLHttpRequestBodyInit | null) {
    this.body = body;
    this.status = FakeXMLHttpRequest.statuses.shift() ?? 204;
    FakeXMLHttpRequest.requests.push(this);
    queueMicrotask(() => {
      const progress = { lengthComputable: true, loaded: fileBytes.size, total: fileBytes.size } as ProgressEvent;
      (this.upload.onprogress as ((event: ProgressEvent) => void) | null)?.(progress);
      this.onload?.call(this as unknown as XMLHttpRequest, {} as ProgressEvent);
      this.onloadend?.call(this as unknown as XMLHttpRequest, {} as ProgressEvent);
    });
  }

  abort() {
    this.onabort?.call(this as unknown as XMLHttpRequest, {} as ProgressEvent);
    this.onloadend?.call(this as unknown as XMLHttpRequest, {} as ProgressEvent);
  }
}

beforeEach(() => {
  FakeXMLHttpRequest.statuses = [];
  FakeXMLHttpRequest.requests = [];
  vi.stubGlobal('XMLHttpRequest', FakeXMLHttpRequest);
});

afterEach(() => vi.unstubAllGlobals());

describe('Listings photo upload HTTP flow', () => {
  it('sends the server-required create-only headers and confirms the stored file', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(response(intent(), 201))
      .mockResolvedValueOnce(response({ upload_id: uploadId, media_type: 'image/png', size_bytes: fileBytes.size }));
    vi.stubGlobal('fetch', withCsrf(fetch));
    FakeXMLHttpRequest.statuses = [204];
    const progress: number[] = [];
    const intentIds: string[] = [];

    const confirmed = await uploadListingImage(
      fileBytes,
      operationId,
      (value) => progress.push(value),
      (value) => intentIds.push(value),
    );

    expect(confirmed).toEqual({ upload_id: uploadId, media_type: 'image/png', size_bytes: fileBytes.size });
    expect(intentIds).toEqual([uploadId]);
    expect(FakeXMLHttpRequest.requests).toHaveLength(1);
    expect(FakeXMLHttpRequest.requests[0].method).toBe('PUT');
    expect(FakeXMLHttpRequest.requests[0].url).toBe(intent().upload_url);
    expect(FakeXMLHttpRequest.requests[0].headers).toEqual(intent().required_headers);
    expect(FakeXMLHttpRequest.requests[0].body).toBe(fileBytes);
    expect(progress.at(-1)).toBe(100);
    expect(fetch.mock.calls[0][1].body).toContain(operationId);
  });

  it('retries a lost confirmation for the same upload without sending photo bytes again', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(response(intent(), 201))
      .mockResolvedValueOnce(response({}, 503))
      .mockResolvedValueOnce(response({ upload_id: uploadId, media_type: 'image/png', size_bytes: fileBytes.size }));
    vi.stubGlobal('fetch', withCsrf(fetch));
    FakeXMLHttpRequest.statuses = [204];
    const onIntent = vi.fn();

    await expect(uploadListingImage(fileBytes, operationId, vi.fn(), onIntent)).rejects.toBeInstanceOf(ListingsApiError);
    const recovered = await uploadListingImage(
      fileBytes,
      operationId,
      vi.fn(),
      onIntent,
      uploadId,
    );

    expect(recovered.upload_id).toBe(uploadId);
    expect(FakeXMLHttpRequest.requests).toHaveLength(1);
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(fetch.mock.calls[2][0]).toBe(`/api/image-uploads/${uploadId}/confirm`);
    expect(onIntent).toHaveBeenCalledTimes(1);
  });

  it('renews an expired upload URL once with the same operation key', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(response(intent(), 201))
      .mockResolvedValueOnce(response(intent('https://private-storage.invalid/renewed'), 201))
      .mockResolvedValueOnce(response({ upload_id: uploadId, media_type: 'image/png', size_bytes: fileBytes.size }));
    vi.stubGlobal('fetch', withCsrf(fetch));
    FakeXMLHttpRequest.statuses = [403, 204];

    const confirmed = await uploadListingImage(fileBytes, operationId, vi.fn(), vi.fn());

    expect(confirmed.upload_id).toBe(uploadId);
    expect(FakeXMLHttpRequest.requests.map((request) => request.url)).toEqual([
      intent().upload_url,
      'https://private-storage.invalid/renewed',
    ]);
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(fetch.mock.calls[0][1].body).toBe(fetch.mock.calls[1][1].body);
  });

  it('confirms a previously stored create-only object after a 412 response', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(response(intent(), 201))
      .mockResolvedValueOnce(response({ upload_id: uploadId, media_type: 'image/png', size_bytes: fileBytes.size }));
    vi.stubGlobal('fetch', withCsrf(fetch));
    FakeXMLHttpRequest.statuses = [412];

    await expect(uploadListingImage(fileBytes, operationId, vi.fn(), vi.fn()))
      .resolves.toMatchObject({ upload_id: uploadId });

    expect(FakeXMLHttpRequest.requests).toHaveLength(1);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(fetch.mock.calls[1][0]).toBe(`/api/image-uploads/${uploadId}/confirm`);
  });

  it('reuses the same operation after a missing object instead of creating another intent', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(response({}, 404))
      .mockResolvedValueOnce(response(intent(), 201))
      .mockResolvedValueOnce(response({ upload_id: uploadId, media_type: 'image/png', size_bytes: fileBytes.size }));
    vi.stubGlobal('fetch', withCsrf(fetch));
    FakeXMLHttpRequest.statuses = [204];

    await expect(uploadListingImage(fileBytes, operationId, vi.fn(), vi.fn(), uploadId))
      .resolves.toMatchObject({ upload_id: uploadId });

    expect(FakeXMLHttpRequest.requests).toHaveLength(1);
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(fetch.mock.calls[1][1].body).toContain(operationId);
  });

  it('does not automatically repeat a rejected byte upload', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response(intent(), 201));
    vi.stubGlobal('fetch', withCsrf(fetch));
    FakeXMLHttpRequest.statuses = [500];

    await expect(uploadListingImage(fileBytes, operationId, vi.fn(), vi.fn()))
      .rejects.toThrow('The photo could not be uploaded. Retry the photo.');

    expect(FakeXMLHttpRequest.requests).toHaveLength(1);
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
