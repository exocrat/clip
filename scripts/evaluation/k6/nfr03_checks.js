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
