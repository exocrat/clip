// Offline candidate only: calculate from phases belonging to one response.
// Failed requests and suspicious values never receive an approximate span.
// This is not a monotonic clock or an approved measurement.
export function phaseTimingPreview(response, outcome) {
  if (outcome !== 'correct') return { eligible: false, reason: 'not_correct' };
  const timings = response?.timings;
  if (!timings || !Number.isFinite(timings.blocked) || !Number.isFinite(timings.duration) ||
      timings.blocked < 0 || timings.duration < 0) {
    return { eligible: false, reason: 'invalid_phase' };
  }
  const total = timings.blocked + timings.duration;
  if (!Number.isFinite(total) || total > 5000) return { eligible: false, reason: 'implausible_span' };
  return { eligible: true, request_ms: timings.duration, approximate_span_ms: total };
}
