import { describe, expect, it } from 'vitest';
import { validateListingForm, type ListingFormValues } from '../src/features/listings/listingForm';

const now = Date.parse('2026-10-21T10:00:00Z');
const values: ListingFormValues = {
  title: ' Test textbook ', description: ' A synthetic item ', category_code: 'books',
  condition_code: 'good', price_rupees: '0', negotiable: false, pickup_area: ' Synthetic area ',
  available_from: '', available_until: '', proof_available: '',
};
const images = ['10000000-0000-4000-8000-000000000002'];

describe('Listings form boundary', () => {
  it('omits a blank optional pickup area and still bounds supplied text', () => {
    for (const area of ['', '   ']) {
      const result = validateListingForm({ ...values, pickup_area: area }, images, now);
      expect(result.errors).toEqual({});
      expect(result.intent).not.toHaveProperty('pickup_area');
    }
    expect(validateListingForm({ ...values, pickup_area: 'x'.repeat(121) }, images, now).errors.pickup_area).toBeDefined();
  });
  it('preserves free price, false negotiability and unstated proof/start', () => {
    const { intent, errors } = validateListingForm(values, images, now);
    expect(errors).toEqual({});
    expect(intent).toMatchObject({ asking_price_paise: 0, negotiable: false, title: 'Test textbook', available_until: null });
    expect(intent).not.toHaveProperty('proof_available');
    expect(intent).not.toHaveProperty('available_from');
    expect(intent).not.toHaveProperty('owner_id');
  });
  it.each(['', '-1', '1.5', '1e3', '9007199254740991'])('rejects a missing, fractional, negative or imprecise price: %s', (price) => {
    expect(validateListingForm({ ...values, price_rupees: price }, images, now).intent).toBeUndefined();
  });
  it('requires confirmed image references and rejects duplicates', () => {
    expect(validateListingForm(values, [], now).errors.images).toBeDefined();
    expect(validateListingForm(values, [...images, ...images], now).errors.images).toBeDefined();
  });
  it('validates trimmed Unicode code-point bounds rather than UTF-16 units', () => {
    expect(validateListingForm({ ...values, title: '🧪'.repeat(120) }, images, now).intent).toBeDefined();
    expect(validateListingForm({ ...values, title: '🧪'.repeat(121) }, images, now).errors.title).toBeDefined();
    expect(validateListingForm({ ...values, title: '   ' }, images, now).errors.title).toBeDefined();
  });
  it.each([['yes', true], ['no', false]] as const)('keeps the explicit %s declaration', (choice, expected) => {
    expect(validateListingForm({ ...values, proof_available: choice }, images, now).intent?.proof_available).toBe(expected);
  });
  it('rejects an end at/before the effective start and serializes valid dates to UTC', () => {
    expect(validateListingForm({ ...values, available_until: '2026-10-21T10:00:00Z' }, images, now).errors.available_until).toBeDefined();
    const { intent } = validateListingForm({ ...values, available_from: '2026-10-21T12:00:00+02:00', available_until: '2026-10-21T13:00:00+02:00' }, images, now);
    expect(intent?.available_from).toBe('2026-10-21T10:00:00.000Z');
    expect(intent?.available_until).toBe('2026-10-21T11:00:00.000Z');
  });
});
