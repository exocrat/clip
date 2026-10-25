# Search and Listings integration — PR #11

PR: <https://github.com/exocrat/clip/pull/11>

This change connects Search's sale discovery, wanted requests, and saved-listing
flows to the real Listings implementation for the local integrated application.
Listings remains responsible for listing records and listing SQL; Search calls
Listings through its public provider and both use the configured PostgreSQL
database.

## What is included

- Search can browse available sale listings, use Listings' categories and
  current listing summaries, check save eligibility, and show saved listings.
- Creating or editing a listing follows the existing Listings workflow. The
  database trigger and worker create its search vectors automatically; Keyword
  and Hybrid search read those vectors and the current listing rows. No test
  copies vectors directly into the database.
- The local browser application uses real Listings, Wanted Request, and Saved
  routes/stores. Its caller is a fixed local test Identity. Conversations is
  not implemented here, so conversation-dependent actions fail safely.
- Discover shows listing photos, Discover and Saved share the same sale card,
  and an already-saved listing cannot be saved again. Wanted cards/save controls
  and seller page-size parsing were corrected.
- A locally buildable optional Linux AMD64 Hybrid image and deployment notes
  are included for later integrated deployment. This PR made no cloud changes.
- Eleven identical evidence files (17,523 repeated lines) were removed; the
  distinct test and evaluation records remain. The Gitleaks exception only
  covers verified SHA-256 fingerprint fields in named evidence files; other
  secret checks remain enabled.

## Checks run

- Python: 1,288 passed, 21 skipped; data: 94 passed.
- Web: 147 passed, 2 skipped; lint, TypeScript checks, and production build
  passed.
- Database wrapper safety: 35 cases. Disposable PostgreSQL integration: 21
  passed, 3 optional model checks skipped; migration, smoke, rollback, and
  reapply checks passed.
- Isolated Listings/browser regressions: 52 passed. API mypy: 8 files.
- Contract checks, boundary scan, formatting, Terraform formatting, and local
  Gitleaks scan passed.
- Hosted CI passed for the first published revision. Before approval, use
  GitHub's checks on the current PR head as the exact-revision result.

## What this does not claim

The local caller is synthetic; real Identity and Conversations remain later
work. The final Search dataset, 20 human-reviewed search queries, formal
LI-CORE/SE-CORE/DATA-READY acceptance, NFR measurements, cloud deployment, and
cloud testing are outside this PR. Hybrid search was exercised locally on fresh
listings; this is not a search-quality or performance result. Typo matching is
limited to its reviewed vocabulary.

See the [integration and deployment notes](../../../architecture/listings-search-deployment.md),
the [integration checklist](integration-checklist.md), and the
[handoff overview](README.md).
