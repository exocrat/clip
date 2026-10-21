# Listings API implementation

`routes.py` mounts create (`POST /listings`), detail read
(`GET /listings/{id}`), owner list (`GET /me/listings`), full replacement
(`PUT /listings/{id}`), availability (`PUT /listings/{id}/availability`),
buyer selection (`PUT /listings/{id}/selection`), offer submission/revision,
and offer withdrawal. Each path matches the reviewed Listings HTTP contract.
`service.py` owns field checks, current-account and seller ownership checks,
image ownership/publication validation, availability and buyer-selection
rules, the serialized offer gate, and safe response shapes.

Full replacement accepts an ordered list of existing image references to keep
and newly confirmed upload IDs to add. The PostgreSQL adapter checks that kept
references belong to the listing, consumes confirmed uploads under the same
transaction, retires omitted images for cleanup, and stores the selected order.
The live schema prohibits unretiring a removed image, so a later re-add must be
a new confirmed upload. Photo bytes and delivery remain LI-02 integrations.

The service depends on a `ListingsStore` adapter. The adapter must use the
Listings schema, call Identity through its public eligibility interface, check
confirmed owner-bound image records, and make listing plus image attachment a
single transaction. It must enforce expected revisions for replacement,
availability, and selection. Its offer guard must serialize an offer against
availability changes and any retirement write while keeping Conversations in
its own transaction. It must replay matching operation IDs and reject
conflicting reuse as specified by the contract. It must not query another
domain's private tables.

Selection uses only the public Conversations participant check. Listing offer
commands use only the public Conversations offer-write call. The selection
and offer endpoints cannot return successful results until those adapters are
injected. A retired listing is treated as absent by the store read/offer guard;
retirement eligibility scanning, marker calls and content/image cleanup are not
implemented in this increment. The exact cleanup implementation remains
outside this step until its separate mechanism/order approval.

The current schema inventory does not define durable replay receipts for
availability and selection operation IDs. The adapter contract below requires
same-intent replay and conflicting-reuse rejection, so that storage detail must
be resolved before the real adapter is wired. No migration has been added.

The API startup currently has no configured Listings store, Identity wiring,
or Conversations adapter. Until those are supplied, the mounted routes fail
closed with the shared 503 error (or 401 when there is no trusted caller
context). No in-memory or fake store is selected by default. A test-only
adapter may be injected by owned test fixtures; its results do not prove
PostgreSQL, Identity, Conversations, or LI-02 storage integration.
