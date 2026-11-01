// Classify the HTTP result without retaining response content or provider errors.
// A 200 still requires the caller to validate the response against the oracle.
export function preliminaryOutcome(response) {
  if ([1050, 1211].includes(response.error_code)) return 'timeout';
  if ([401, 403].includes(response.status)) return 'unauthorized';
  if (response.status === 429) return 'throttled';
  if (response.status === 0) return 'transport_error';
  if (response.status !== 200) return 'http_error';
  return 'requires_correctness_check';
}
