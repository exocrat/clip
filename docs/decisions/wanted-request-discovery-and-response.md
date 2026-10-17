# Wanted-request discovery and seller responses

**Date:** 2026-10-17

## Question

How can potential sellers discover wanted requests and contact their authors,
and how should that fit with the author's private management view and
temporary-account limits?

## Options considered

- Keep requests visible only to their author. This prevents potential sellers
  from finding them and leaves only draft-time matching against sale listings.
- Publish open requests in public discovery and let eligible members contact the
  author through the platform. This makes requests discoverable while preserving
  private contact details and conversation content.

## Selected choice

- Public discovery at `/` has a Sale Listings / Wanted Requests toggle. Open
  wanted requests have public detail pages and a Contact requester action.
- The action starts a private conversation associated with the wanted request.
  A responder does not need to have an existing sale listing.
- Public request details do not expose the author's private contact information.
  Conversation access remains participant-authorized, including for direct URL
  or ID attempts.
- Temporary accounts may browse wanted requests but may not start a response
  conversation; they are new freshers without items to sell. Other approved
  temporary-account capabilities are unchanged.
- The author manages only their own wanted requests from `/my/listings`, which
  may also provide a Sale Listings / Wanted Requests toggle. The author can mark
  a request unavailable when it is no longer wanted.
- Sale Listings and Wanted Requests remain distinct backend objects. This
  decision does not define their schemas or type taxonomy.
- A weekly wanted-request email digest remains optional. It may link to public
  request details and must not include private conversation or contact data.
  It remains separate from optional new-sale-to-wanted-request match alerts.

## Rationale

Potential sellers need a place to learn what people want and a safe way to offer
help. A public request page plus participant-only conversation provides that
path without disclosing contact information or requiring the responder to
publish an item first. The author's management view remains scoped to their own
posts.

## Implications

- `docs/product/product-reference-and-architecture-decisions.md` records this as
  a team clarification, not a change to the submitted PRD or a new FR identifier.
- `docs/tasks/domain-task-list.md` assigns public discovery, author management,
  response authorization, request-associated conversations, inbox behavior, and
  integrated checks to their owning tasks.
- `docs/tasks/project-task-index.md` and
  `docs/architecture/task-dependencies.dot` include the real integration
  dependencies for request-based conversations.
- The human-verified frontend route and ownership map is in
  `docs/architecture/frontend-collaboration.md`; Step 3 recorded the page
  contributors and public component boundaries.
- DL-00 and the affected domain owners must still define query fields and
  ordering, request-to-conversation association and duplicate behavior, and what
  happens to existing conversations when a request is closed. This record does
  not choose those contract details.
- The optional digest retains its existing recipient, subscription, schedule,
  unsubscribe, deduplication, privacy, failure, and cost decision gates.

## Approver

Suraj — verified in the PD-07 frontend handoff discussion on 2026-10-17.

## Supersedes

None. This resolves the earlier private-only wanted-request discovery proposal.
