/** Short capacity checks are loopback-only diagnostics, never deployed profiles.
 * Keep reviewed profiles unchanged and validate them before calling this helper.
 * Real runners reject the flag rather than silently shortening formal evidence.
 */
export function localCapacityWindow(env, realMode, profile) {
  const flag = env.CLIP_CAPACITY_LOCAL_SHORT;
  if (flag !== undefined && flag !== 'true') throw Error('invalid_local_capacity_flag');
  if (flag === 'true' && realMode) throw Error('short_capacity_forbidden_on_real_target');
  return flag === 'true'
    ? { warmup_seconds: 10, measured_seconds: 60 }
    : { warmup_seconds: profile.warmup_seconds, measured_seconds: profile.measured_seconds };
}
