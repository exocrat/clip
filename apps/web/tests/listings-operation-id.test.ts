import { afterEach, describe, expect, it, vi } from 'vitest';
import { newOperationId } from '../src/features/listings/operationId';

afterEach(() => vi.unstubAllGlobals());

describe('Listings operation IDs on HTTPS and HTTP', () => {
  it('uses the native cryptographic UUID when available', () => {
    const randomUUID = vi.fn(() => '10000000-0000-4000-8000-000000000001');
    const getRandomValues = vi.fn();
    vi.stubGlobal('crypto', { randomUUID, getRandomValues });
    expect(newOperationId()).toBe('10000000-0000-4000-8000-000000000001');
    expect(randomUUID).toHaveBeenCalledOnce();
    expect(getRandomValues).not.toHaveBeenCalled();
  });

  it('creates a UUID v4 from secure random bytes when HTTP omits randomUUID', () => {
    const getRandomValues = vi.fn((bytes: Uint8Array) => {
      for (let index = 0; index < bytes.length; index += 1) bytes[index] = index;
      return bytes;
    });
    vi.stubGlobal('crypto', { getRandomValues });
    expect(newOperationId()).toBe('00010203-0405-4607-8809-0a0b0c0d0e0f');
    expect(getRandomValues).toHaveBeenCalledOnce();
    expect(getRandomValues.mock.calls[0][0]).toHaveLength(16);
  });

  it('requires secure randomness when the native UUID method is absent', () => {
    vi.stubGlobal('crypto', { getRandomValues: () => { throw new Error('randomness unavailable'); } });
    expect(() => newOperationId()).toThrow('randomness unavailable');
  });
});
