# Search integration resume checklist

Resume the earliest pending original checkpoint when its provider arrives. Do not
silently start SE-02 Step9 or accept a milestone using isolated results.

| Dependency / coordinator | Required handoff | Resume checks |
|---|---|---|
| Identity A: ID-READY | Accepted exact revision, real server session context/GET /me, current check_account_eligibility and supported runtime config | SE-01 auth and SE-02 Steps3/6/7/8: regular/temporary/expired/revoked; no client actor selector; temporary wanted management/browse allowed, response forbidden |
| Listings B with Search C | LI-CORE accepted revision; reviewed real query_available_listings, active/historical category, read_save_target and read_saved_listing_summaries bindings | SE-01 Steps2–5/10 and SE-02 Steps2/4/5/8: schema/code-FKs, available-only stable results, title-only draft bounds, saved target checks, current unavailable/future/ended and retired placeholder, own-page-only resolver scope |
| Search C: SE-CORE | Real Identity/Listings integration, exact revision, local gates and independent human review/merge | Resume named consumers only after actual acceptance; local preview is insufficient |
| Conversations D with Search C | Real wanted create-or-existing and exact-pair read-only lookup, origin activity and retirement marker; participant/uniqueness/locking guarantees | SE-02 Steps3/6/8 and INT-01: self/temporary/retired/pending denial, closed existing-only, lost response retries, same-pair races, close/retirement serialization, all-thread90day activity, no new offers/threads after retirement |
| Dataset/labels: Search C + human label reviewer | Accepted real generator/schema/image references; >=5000users/>=1000listings; frozen fingerprint; >=20 manually reviewed query judgments | SE-01 Steps2/9/11: repeated generation/load validation, final evaluator adapter and result capture, fixed labels, Success@5>=80% with query-level failures retained |
| Browser verifier: Mohit | Actual browser/OS, portrait/landscape dimensions and supported physical-phone keyboard observations | SE-01/SE-02 UI integrated flows, focus/retry/error states; no device claim from desktop resizing |
| Shared runtime operator + Mohit | Exact approved revision/environment, migrations/build/deploy/readiness route; separately approved cloud caps/cost/cleanup if needed | SE-02 Step8 shared DB/runtime; SE-01 Steps12–14 final workload measurements, real auth and dataset |
| Local/CI operator + independent reviewers | Pinned secret scan, actual Docker database gate or separately reviewed equivalent, exact-head hosted CI, independent designated human approval | SE-01 Step15/SE-02 Step9; full diff and cross-domain owner review. Each commit/push/merge needs its separate approval |

No outbound teammate message, PR creation, fetch/merge, cloud operation or task
reassignment is authorized by this checklist. Interfaces must be implemented through
the owning public boundary; generated declaration files must not be hand-edited.
