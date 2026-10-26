# SE-02 Step7 frontend verification package

Implemented; Mohit verified this isolated UI result (2026-10-25 08:28:21 UTC). Exact browser, viewport and physical-phone observations were not supplied and are not inferred. Branch: `search-domain`;
uncommitted accumulated work; no publication/merge/cloud action. Full SE-02 and
its real integration gates remain incomplete. Step6 isolated result was verified
before this authorized increment. Audit of Step7 against contracts and ownership
found no new task-definition gap: reviewed GET /me supplies eligibility.

Open http://127.0.0.1:5173 on this Mac while the preview is running. A restart
command and precise effects are registered in docs/environment/commands.md.
Fresh fixture cluster for final checks: `/tmp/clip-listings-test-gsr2jhwc`.
Earlier `/tmp/clip-listings-test-w1i6ul82` was stopped cleanly before restart;
sandbox init failure retained `/tmp/clip-listings-test-kpwaxpn1` without a server.

The isolated banner identifies real Search SQL and real native draft queries,
synthetic Identity and fixed saved-state snapshots. No real Conversations or
image delivery is supplied. Available listing details use the real Listings
service. This harness does not test changing upstream saved snapshots, real
revocation/account switching or actual conversation membership/uniqueness.
Those remain integration obligations. Existing backend tests cover denied,
temporary, expiry, retirement, concurrency and upstream transitions in isolation.

## Browser review actions (result verified; detailed device observations unreported)

1. Discovery → Wanted Requests: browse public requests and open another author's
   Bicycle wanted request. Contact requester must show a safe unavailable message,
   retaining the page; it cannot produce a fake conversation or expose contacts.
2. My listings → Wanted Requests: create a request. Enter Bicycle to see live
   title-only possible matches before publication. Try a nonmatch and blank title.
   Matches are advisory; publishing is independent. Try blank budget and0;
   decimal/negative inputs must be refused without losing the draft.
3. Edit your request, clear or set its budget, save changes. Mark unavailable;
   check exclusion from public browse and continued private/detail visibility.
   Reopen the same request. Refresh after concurrent/stale-revision errors.
4. Saved: check available and unavailable fixtures. Remove the available item,
   visit it from sale discovery, then use Save listing on detail; confirm it
   returns to Saved. Photo delivery is intentionally unavailable in this harness.
   Retired placeholder validation is automated; a retired demo fixture is not seeded.
5. Check loading, empty, retry and failed-action presentation. The normal runtime
   with missing providers must remain unavailable, not inherit preview success.
6. Repeat desktop, narrow portrait and landscape; inspect tab/focus, form labels,
   long text, no horizontal page overflow and reachable buttons. Report actual
   browser/OS/dimensions. Phone on-screen keyboard verification is still pending;
   resizing the desktop is layout evidence only. No phone exposure is authorized.

## Automated evidence

See result.json. Default web suite:144passed,2explicit opt-in network tests skipped;
opt-in final native HTTP run:2passed. Python preview safety suites:23passed.
Black2files, boundaries0, generated artifacts8current, types/build/lint and whitespace
checks pass. No full root Python/native aggregate rerun claimed for this UI-only
production change; Step6's earlier results remain historical evidence. No hosted
CI, independent peer review, final secret scan or real-provider acceptance claimed.
Initial sandbox network checks failed; equivalent escalated fixed-loopback runs
passed. Contract freshness first lacked local Node PATH; rerun with pinned PATH
passed. Formatter CLI options were rejected before formatting; a temporary config
formatted only the five new TS/TSX/test files, without changing repo formatter policy.
