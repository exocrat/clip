import { SUMMARY_FIELDS } from './core.js';
/** Public Wanted-page correctness while the same workload creates newer rows.
 * Fixture existence is checked separately before measurement. Correct pagination
 * can displace it; every returned row must still satisfy shape, uniqueness/order.
 */
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
export function validWantedItem(item) {
  return item && typeof item === 'object' && uuid.test(item.request_id) &&
    typeof item.title === 'string' && item.title.trim().length > 0 && item.title.length <= 120 &&
    typeof item.description === 'string' && item.description.trim().length > 0 && item.description.length <= 5000 &&
    typeof item.category_code === 'string' && typeof item.category_label === 'string' &&
    (item.budget_paise == null || (Number.isSafeInteger(item.budget_paise) && item.budget_paise >= 0)) &&
    typeof item.created_at === 'string' && Number.isFinite(Date.parse(item.created_at)) &&
    typeof item.updated_at === 'string' && Number.isFinite(Date.parse(item.updated_at));
}
export function validWantedPage(body) {
  if (!body || body.page !== 1 || body.page_size !== 20 || typeof body.has_next !== 'boolean' ||
      !Array.isArray(body.items) || !body.items.length || body.items.length > 20 ||
      (body.has_next && body.items.length !== 20) || !body.items.every(validWantedItem)) return false;
  if (new Set(body.items.map(item => item.request_id)).size !== body.items.length) return false;
  return body.items.every((item, index) => index === 0 ||
    body.items[index - 1].created_at > item.created_at ||
    (body.items[index - 1].created_at === item.created_at && body.items[index - 1].request_id > item.request_id));
}


/** Verify the actual scheduled-listing create result, including attached image.
 * Its future availability is an explicit fixture choice, never a weakened
 * browse oracle. The owner view is reconciled separately after measurement.
 */
export function validListingCreate(body, command) {
  const keys = [...SUMMARY_FIELDS, 'proof_available'];
  if (!body || Object.keys(body).length !== keys.length || !keys.every(k => Object.hasOwn(body, k)) || !uuid.test(body.listing_id)) return false;
  for (const key of ['title','description','category_code','condition_code','asking_price_paise','original_price_paise','negotiable','pickup_area','available_until','proof_available']) if (body[key] !== command[key]) return false;
  if (Date.parse(body.available_from) !== Date.parse(command.available_from) || body.availability !== 'available' || typeof body.sensitive_purchase !== 'boolean') return false;
  if (![body.category_label,body.condition_label].every(v => typeof v === 'string' && v.length > 0)) return false;
  return Array.isArray(body.image_ids) && body.image_ids.length === 1 && body.image_ids.every(id => uuid.test(id));
}
