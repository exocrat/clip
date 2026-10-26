# Search domain test coverage — SE-02 Step6

The canonical case list is [SE-02 Step6](../../../../../docs/tasks/domain-task-list.md).
These tests establish isolated behavior against reviewed contracts. Full pytest
success does not establish real provider or complete feature coverage.

| Required case | Existing/local evidence | Remaining gate |
|---|---|---|
| Owner/nonowner request create/edit/close/reopen | `test_wanted_postgres.py`, `test_step6_postgres.py` run actual HTTP/SQL/revisions | Real Identity and category providers |
| Open public reads, unavailable exclusion and owner exception | Both wanted native files; safe public projection and owned unavailable detail | Real sessions/discovery integration |
| Regular/temporary browse and own management | `test_wanted.py`, `test_step6_postgres.py`, `test_saved_postgres.py` | Actual account capability/provider wiring |
| Regular/temporary response initiation | `test_wanted_response.py` and native response test: regular only, temp denial before origin/C, current eligibility, self/hidden denial | Actual C independent capability/participant enforcement |
| Expiry | Unit auth checks plus every implemented wanted operation in `test_step6_postgres.py`; saved/draft guards | Actual temporary-account lifetime/revocation via Identity |
| Omitted/null/zero budgets and edit omission | Wanted unit/native files; Step6 create variants for both classes and normalized retry | Real upstream author/category integration |
| Unicode description bounds | `test_wanted.py`: trim before 5000 code points, multibyte accepted, blank/excess rejected | UI limits checked at Step7 |
| Draft match/nonmatch/unavailable exclusions | `test_draft_matches_postgres.py` actual Listings query/SQL; bounded/no persistence | Actual Identity and public provider composition |
| Duplicate saves/retries/unsave/cross-user scope | `test_saved_postgres.py` real Search rows/locks plus unit scripts | Actual target/saved-summary providers |
| Listing availability transition and saved references | Native saved test changes actual source; explicit current-state fixture | Real public resolver transition/integrity |
| Future/ended saved views | `test_saved.py`: retain current summary outside discovery window | Actual resolver/window/UI behavior |
| 180/90-day cutoffs and anchor reset | `test_wanted_retirement.py` and native retirement tests; exact boundaries, pair fences | Real Conversations activity/marker integration |
| Recent activity in any associated conversation | Coordinator tests handle reported aggregate/latest and blocked outcome | Actual C all-thread activity/lock checks; not proved by a double |
| No reopen after retirement; retained retry keys | Actual native retirement tests and wanted tests | Real C participant-write integration |
| No new response after retirement/close; close-versus-response race | Native response test: retired/pending404; closed existing-only; actual Search close-first/response-first row locks | Actual C provider/unique pair/race integration |
| No offer on retired/request origin | Public policy and retained marker boundary; no Search offer implementation | CN-01/CN-02 participant/offer enforcement integration |
| Saved retired-content privacy | Native saved parent retirement + explicit placeholder fixture; inconsistent response rejected | Actual public resolver retirement behavior |
| Pagination | Step6 wanted tied owner/public pages and hidden-before-page; saved tied pages/own IDs/reordered provider; draft first20/has_more | Real provider/API/UI integration |
| Dependency failures and retry ambiguity | Saved/draft unit/native and retirement timeout/cancel/lost-result/rollback tests | Response lost-result/closed lookup tested locally; actual providers pending |

`test_step6_postgres.py` closes only its own public fixture requests on exit so
later tests have no extra discovery corpus. Immutable origins/receipts remain.
Registered database wrappers execute it on their private owned target; nothing
is inserted into an existing/shared/live database. Saved's large committed
pagination corpus still runs last after bounded mathematical bootstrap checks.

The response endpoint and200 body were corrected in the approved implementation checkpoint.
Tests do not count the explicit C fixture as a real Conversations implementation.
The [original coverage evidence](../../../../../docs/evaluation/domain/se-02/test-coverage/result.json)
preserves the original gaps; [response correction evidence](../../../../../docs/evaluation/domain/se-02/wanted-response/result.json)
records the resolved local inventory and remaining real gates.
