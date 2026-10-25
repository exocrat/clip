# Draft title

Implement Search discovery, wanted requests and private saved listings in isolated mode

# Draft description

Adds keyword/hybrid listing discovery with filters, stable pagination, relevance
sorting and bounded known-vocabulary typo tolerance. Adds wanted-request author
management, public browse/detail, advisory draft matches, private saved-listing
management and regular-member response initiation through reviewed contracts.

The implementation includes native PostgreSQL migrations/locking/retry/privacy
checks, responsive Search UI composition, local semantic/load tooling and explicit
failure states. Retired origins retain only approved minimal references; unavailable
saved listings remain visible. Missing real providers fail safely unavailable.

This is an implementation-only handoff. ID-READY, LI-CORE, SE-CORE and DATA-READY
are not accepted. Real Identity/Listings/Conversations integration, final dataset
and human query labels, final evaluator binding, device coverage and all final
NFR measurements remain pending. The preview does not establish real auth or
conversation creation. Neither SE-01 nor SE-02 is complete.

Local validation:1270Python tests,94data tests,144web tests, Black183files,
contracts8current, boundaries0, CI parity11, double-typecheck1file and
35database-wrapper safety cases pass. Fresh native PostgreSQL14migration down/up/
repeat/schema checks and20tests pass;3optional model checks skipped. Web's2opt-in
HTTP tests are skipped by default and previously passed separately at Step7.
Actual Docker/secret scanning and exact-head hosted CI are still pending.

Review the complete changed-file inventory, canonical decisions and
integration-checklist.md. Listings/Identity reviewers and Conversations review
are required where affected. Arrange an independent human review using
`docs/prompts/peer-review-prompt.md`; AI findings are not human approval.

Publication state: draft text only. No commit/head/PR URL exists for this handoff.
Before publication, inspect the exact staged diff, settle coherent PR scope,
run the missing checks, obtain explicit commit/push approval, and bind results to
the committed revision. Merge requires separate authorization of the exact PR head.
