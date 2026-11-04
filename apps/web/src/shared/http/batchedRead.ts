/** Coalesce one render's reads without retaining private results across pages/users.
 * Each caller owns cancellation. The shared request is cancelled only when every
 * caller has left; cancelled callers never receive results. No retry or cache.
 */
export function batchedRead<Value>(
  load: (keys: string[], signal: AbortSignal) => Promise<Map<string, Value>>,
  maximum = 100,
) {
  type Item = { key: string; signal?: AbortSignal; resolve: (value: Value) => void;
    reject: (error: unknown) => void; cancelled: boolean; abort?: () => void };
  let queued: Item[] = [];
  let scheduled = false;

  async function flush() {
    scheduled = false;
    const pending = queued;
    queued = [];
    for (let offset = 0; offset < pending.length; offset += maximum) {
      const items = pending.slice(offset, offset + maximum);
      const controller = new AbortController();
      for (const item of items) {
        item.abort = () => {
          item.cancelled = true;
          item.reject(new DOMException('Read cancelled', 'AbortError'));
          if (items.every((entry) => entry.cancelled)) controller.abort();
        };
        item.signal?.addEventListener('abort', item.abort, { once: true });
        if (item.signal?.aborted) item.abort();
      }
      try {
        const keys = [...new Set(items.filter((item) => !item.cancelled).map((item) => item.key))];
        if (!keys.length) continue;
        const values = await load(keys, controller.signal);
        if (items.some((item) => !item.cancelled && !values.has(item.key))) throw new Error('Incomplete batch response');
        for (const item of items) {
          if (item.cancelled) continue;
          item.resolve(values.get(item.key) as Value);
        }
      } catch (error) {
        for (const item of items) if (!item.cancelled) item.reject(error);
      } finally {
        for (const item of items) if (item.abort) item.signal?.removeEventListener('abort', item.abort);
      }
    }
  }

  return (key: string, signal?: AbortSignal): Promise<Value> => {
    if (signal?.aborted) return Promise.reject(new DOMException('Read cancelled', 'AbortError'));
    return new Promise((resolve, reject) => {
      queued.push({ key, signal, resolve, reject, cancelled: false });
      if (!scheduled) {
        scheduled = true;
        setTimeout(() => { void flush(); }, 0);
      }
    });
  };
}
