import { describe, expect, it, vi } from 'vitest';
import { createDisplayedReadAcknowledger } from '../src/features/conversations/read-state';

describe('display-driven conversation read state', () => {
  it('does not acknowledge fetched entries until explicitly told they were displayed', async () => {
    const acknowledge = vi.fn(async (_sequence: number) => undefined);
    const afterRender = createDisplayedReadAcknowledger(acknowledge);

    expect(acknowledge).not.toHaveBeenCalled();
    await afterRender(4);

    expect(acknowledge).toHaveBeenCalledExactlyOnceWith(4);
  });

  it('serializes acknowledgements and never moves the watermark backwards', async () => {
    const acknowledge = vi.fn(async (_sequence: number) => undefined);
    const afterRender = createDisplayedReadAcknowledger(acknowledge, 2);

    await Promise.all([afterRender(5), afterRender(3), afterRender(8)]);

    expect(acknowledge.mock.calls.map(([sequence]) => sequence)).toEqual([5, 8]);
  });

  it('allows a failed acknowledgement to be retried without treating it as committed', async () => {
    const acknowledge = vi
      .fn<(_sequence: number) => Promise<void>>()
      .mockRejectedValueOnce(new Error('synthetic failure'))
      .mockResolvedValueOnce(undefined);
    const afterRender = createDisplayedReadAcknowledger(acknowledge);

    await expect(afterRender(7)).rejects.toThrow('synthetic failure');
    await afterRender(7);

    expect(acknowledge).toHaveBeenCalledTimes(2);
  });

  it('rejects invalid display cursors', async () => {
    const acknowledge = vi.fn(async (_sequence: number) => undefined);
    const afterRender = createDisplayedReadAcknowledger(acknowledge);

    await expect(afterRender(-1)).rejects.toThrow(RangeError);
    expect(acknowledge).not.toHaveBeenCalled();
  });
});
