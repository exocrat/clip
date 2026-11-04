import { afterEach, expect, it, vi } from 'vitest';
import { readImageDelivery } from '../src/features/listings/listingsApi';

const id = (n: number) => `30000000-0000-4000-8000-${String(n).padStart(12, '0')}`;
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

it('batches photo links and isolates a hidden image without failing other photos', async () => {
  const delivery = { url: 'https://storage.example.invalid/synthetic-link', url_expires_at: new Date(Date.now() + 240000).toISOString() };
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [
    { image_id: id(1), delivery }, { image_id: id(2), delivery: null },
  ] }), { status: 200 }));
  vi.stubGlobal('fetch', fetch);
  const visible = readImageDelivery(id(1));
  const hidden = readImageDelivery(id(2));
  await expect(visible).resolves.toEqual(delivery);
  await expect(hidden).rejects.toMatchObject({ status: 404 });
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('rejects an expired link rather than returning it to an image element', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [
    { image_id: id(1), delivery: { url: 'https://storage.example.invalid/expired', url_expires_at: new Date(Date.now() - 1000).toISOString() } },
  ] }), { status: 200 })));
  await expect(readImageDelivery(id(1))).rejects.toMatchObject({ status: 503 });
});

it('preserves same-origin loopback image previews without allowing public HTTP links', async () => {
  const response = (url: string) => new Response(JSON.stringify({ items: [
    { image_id: id(1), delivery: { url, url_expires_at: new Date(Date.now() + 240000).toISOString() } },
  ] }), { status: 200 });
  vi.stubGlobal('window', { location: new URL('http://127.0.0.1:5174') });
  const fetch = vi.fn()
    .mockResolvedValueOnce(response('http://127.0.0.1:5174/__listings_demo/storage/synthetic'))
    .mockResolvedValueOnce(response('http://storage.example.invalid/synthetic'));
  vi.stubGlobal('fetch', fetch);
  await expect(readImageDelivery(id(1))).resolves.toMatchObject({ url: 'http://127.0.0.1:5174/__listings_demo/storage/synthetic' });
  await expect(readImageDelivery(id(1))).rejects.toMatchObject({ status: 503 });
});

it.each([-600000, 600000])('uses API time for photo expiry when the browser clock differs by %i ms', async (skew) => {
  const serverNow = Date.now();
  const delivery = { url: 'https://storage.example.invalid/synthetic-link', url_expires_at: new Date(serverNow + 240000).toISOString() };
  vi.spyOn(Date, 'now').mockReturnValue(serverNow + skew);
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [
    { image_id: id(1), delivery },
  ] }), { status: 200, headers: { Date: new Date(serverNow).toUTCString() } })));
  await expect(readImageDelivery(id(1))).resolves.toEqual(delivery);
});
