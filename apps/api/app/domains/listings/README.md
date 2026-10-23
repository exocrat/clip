# Listings API implementation

`routes.py` mounts image-upload intent (`POST /image-uploads`), confirmation
(`POST /image-uploads/{upload_id}/confirm`), cancellation
(`DELETE /image-uploads/{upload_id}`), and authorized image delivery
(`GET /images/{image_id}/delivery`), plus create (`POST /listings`), detail read
(`GET /listings/{id}`), owner list (`GET /me/listings`), full replacement
(`PUT /listings/{id}`), availability (`PUT /listings/{id}/availability`),
buyer selection (`PUT /listings/{id}/selection`), offer submission/revision,
and offer withdrawal. Each path matches the reviewed Listings HTTP contract.
`service.py` owns field checks, current-account and seller ownership checks,
owner-bound upload intent/confirmation, image ownership/publication validation,
availability and buyer-selection rules, the serialized offer gate, and safe
response shapes. Before image delivery, it checks that the image remains
attached to a retained listing and applies the same owner/discoverability rule
as listing details. `s3_storage.py` signs create-only PUT requests and short-lived
GET requests against the private bucket, and reads storage metadata through the
server's AWS credentials or task role. Image GET links expire within five
minutes, are marked `private, no-store`, and are returned without exposing the
object key. The bucket is not made public.

Full replacement accepts an ordered list of existing image references to keep
and newly confirmed upload IDs to add. The PostgreSQL adapter checks that kept
references belong to the listing, consumes confirmed uploads under the same
transaction, retires omitted images for cleanup, and stores the selected order.
The live schema prohibits unretiring a removed image, so a later re-add must be
a new confirmed upload. Responsive upload and gallery UI remain Step 9 of LI-02.

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
injected. A retired listing is treated as absent by the store read/offer guard.
Retirement is finalized only after the public Conversations marker confirms it;
Listings then scrubs its content and marks its images retired.

LI-02's image upload intent migration persists the owner-scoped operation ID
and initially declared media metadata. This makes retries return the same
upload intent while rejecting reuse of an operation ID for different metadata.
Older rows are backfilled with their own upload ID as a one-time operation key.
The migration does not alter listing or identity data.

The separate schema inventory still does not define durable replay receipts
for availability and selection operation IDs; that existing adapter detail
remains unresolved and is outside the image-upload migration.

The API startup currently has no configured Listings store, Identity wiring,
or Conversations adapter. Until those are supplied, the mounted routes fail
closed with the shared 503 error (or 401 when there is no trusted caller
context). No in-memory or fake store is selected by default. Cancellation marks
an unattached upload failed but retains its object key for cleanup. Confirmation
checks uploaded file signatures, actual S3 size, and content metadata before
marking the image confirmed. The internal `cleanup_image_objects` operation
processes at most 100 records by default and 500 at most per pass. It handles
retired images and expired unattached uploads, deletes S3 objects before their
database references, and delays failed/unknown deletes by five minutes so
other work can proceed. It is a worker operation, not a public HTTP route; no
cleanup schedule is installed here. Its migration adds per-object retry times
and due-work indexes; expired upload rows are made terminal under a database
lock before S3 deletion, preventing a concurrent confirmation or listing edit
from publishing an object being removed. A test-only adapter may be injected
by owned test fixtures; its results do not prove PostgreSQL, Identity,
Conversations, or LI-02 storage integration.
