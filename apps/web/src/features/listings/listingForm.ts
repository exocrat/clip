import type { CreateListingRequest } from './listingsApi';

export type ListingFormValues = {
  title: string;
  description: string;
  category_code: string;
  condition_code: string;
  price_rupees: string;
  negotiable: boolean;
  pickup_area: string;
  available_from: string;
  available_until: string;
  proof_available: '' | 'yes' | 'no';
};

export type ListingFormErrors = Partial<Record<keyof ListingFormValues | 'images', string>>;
export type CreateListingIntent = Omit<CreateListingRequest, 'operation_id'>;
export type ListingFieldsIntent = Omit<CreateListingIntent, 'image_upload_ids'>;

/** Validate and translate seller-entered listing details to the API field shape. */
export function validateListingFields(
  values: ListingFormValues,
  now = Date.now(),
  requireStart = false,
): { errors: ListingFormErrors; fields?: ListingFieldsIntent } {
  const errors: ListingFormErrors = {};
  const requiredMessages = {
    title: 'Add a title for your item.',
    description: 'Describe the item you are selling.',
  };
  for (const [field, maximum] of [['title', 120], ['description', 5000]] as const) {
    const length = [...values[field].trim()].length;
    if (!length) errors[field] = requiredMessages[field];
    else if (length > maximum) errors[field] = `Use ${maximum} characters or fewer.`;
  }
  if ([...values.pickup_area.trim()].length > 120) {
    errors.pickup_area = 'Keep the pickup area to 120 characters or fewer.';
  }
  if (!values.category_code) errors.category_code = 'Choose an item category.';
  if (!values.condition_code) errors.condition_code = 'Choose the item condition.';
  const paise = Number(values.price_rupees) * 100;
  if (!values.price_rupees.trim()) {
    errors.price_rupees = 'Enter an asking price. Use 0 if the item is free.';
  } else if (!/^\d+$/.test(values.price_rupees)) {
    errors.price_rupees = 'Enter a price in whole rupees, such as 500. Use 0 for a free item.';
  } else if (!Number.isSafeInteger(paise)) {
    errors.price_rupees = 'That amount is too large. Enter a smaller price.';
  }
  const start = values.available_from ? new Date(values.available_from).getTime() : now;
  const end = values.available_until ? new Date(values.available_until).getTime() : null;
  if (requireStart && !values.available_from) {
    errors.available_from = 'Choose when the listing becomes available.';
  }
  if (!Number.isFinite(start)) errors.available_from = 'Enter a valid start date and time.';
  if (end !== null && (!Number.isFinite(end) || end <= start)) {
    errors.available_until = values.available_from
      ? 'Choose an end date after the start date.'
      : 'Choose an end date in the future.';
  }
  if (Object.keys(errors).length) return { errors };
  return {
    errors,
    fields: {
      title: values.title.trim(), description: values.description.trim(),
      category_code: values.category_code, condition_code: values.condition_code,
      asking_price_paise: paise, negotiable: values.negotiable,
      ...(values.pickup_area.trim() ? { pickup_area: values.pickup_area.trim() } : {}),
      ...(values.available_from ? { available_from: new Date(start).toISOString() } : {}),
      available_until: end === null ? null : new Date(end).toISOString(),
      ...(values.proof_available === '' ? {} : { proof_available: values.proof_available === 'yes' }),
    },
  };
}

/** Validate a create form plus its required, ordered upload references. */
export function validateListingForm(
  values: ListingFormValues,
  imageIds: string[],
  now = Date.now(),
): { errors: ListingFormErrors; intent?: CreateListingIntent } {
  const result = validateListingFields(values, now);
  const errors = result.errors;
  if (imageIds.length < 1 || imageIds.length > 8 || new Set(imageIds).size !== imageIds.length) {
    errors.images = 'Add between 1 and 8 different photos before publishing.';
  }
  if (Object.keys(errors).length || !result.fields) return { errors };
  return { errors, intent: { ...result.fields, image_upload_ids: imageIds } };
}
