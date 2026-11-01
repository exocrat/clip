// Initialization-only bridge check. Never execute this as a workload.
import timer from 'k6/x/clipmonotonic';

function expectFailure(action, label) {
  let failed = false;
  try { action(); } catch (_) { failed = true; }
  if (!failed) throw new Error(label);
}

expectFailure(() => timer.stop(), 'stop_without_start_accepted');
timer.start();
expectFailure(() => timer.start(), 'duplicate_start_accepted');
const elapsed = timer.stop();
if (!Number.isFinite(elapsed) || elapsed < 0) throw new Error('invalid_elapsed');
expectFailure(() => timer.stop(), 'duplicate_stop_accepted');
console.log('clock_bridge_check_passed');

export default function () { throw new Error('inspection_only'); }
