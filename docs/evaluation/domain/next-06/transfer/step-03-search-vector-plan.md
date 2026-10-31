# NEXT-06 Step3 — automatic Search vector integration through existing APIs

Mohit verified the narrowed scope: Listings belongs to Suraj. This checkpoint
uses that existing implementation solely to verify Search's automatic vector
publication and refresh. It does not implement Listings or require Mohit to
exercise its create/edit UI. It supersedes the manual walkthrough in
step-03-workflow-live-plan.md. No later numbered task step advances here.

## Exact check

The operator page automates one authenticated upload/confirm/create, waits until
the new listing has current two-part vectors and appears in Hybrid search, edits
its text through the existing versioned API, and verifies refreshed vectors and
search again. It uses a small supplied real photo because the normal create
contract requires an owner-confirmed image; attaching someone else's reference
image would bypass ownership. It also hashes/decodes the signed downloaded photo.
No listing/domain source or product UI is changed. Sign-in and image-owner receipts
already retained are reused within their original scope, not retested as a full
Identity/Listings acceptance matrix. This check adds the missing vector path.

Actual Identity session/cookie/CSRF/Microsoft validator, canonical SQL constraints,
public Listings APIs, production model/helper/dispatcher/worker and private S3
adapter are used. No test caller, fabricated session, synthetic provider assertion,
manual vector encoding/publication or copied browser cookie. Fresh local crypto
keys protect only this invocation's new local DB; shared keys/SSMvalues are not read.
Normal API anonymous requests remain401 in the actual local startup check.

## Commands after separate live approval

Backend command

`CLIP_ENVIRONMENT=test .venv/bin/python -m scripts.evaluation.reference_workflow_local --approved-live-local --seconds 1800`

Frontend command

`PATH="$PWD/.tools/node/bin:$PATH" VITE_MICROSOFT_SIGN_IN_ENABLED=true .tools/node/bin/npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`

The agent starts/stops both. Human signs in at **http://localhost:5173/sign-in**,
finishes normal Handle setup if needed, opens
**http://localhost:5173/api/__next06_search_check__** and clicks
**Run Search integration check**. The tool performs the public API create/edit,
not the human. A successful driver requests server shutdown; otherwise30min API
timer/user stop applies. Agent verifies owned processes/model/cluster stopped
and preserves aggregate witnesses; human confirms displayed result. Never paste
passwords, assertions, cookies or signed URLs into chat.

## Exact live cloud/provider scope

- Account335523638354, non-root profilemohitmahapa1/IAMuser same name, Mumbai only.
  Review hashes and explicit approval flag must pass before SDK construction.
- At most5metadata calls: STSidentity; HEAD/owner, public-access-block,
  policy-status and encryption of clip-test-listings-images-ap-south-1-id01.
  Require private/AES256default. No bucket CORS permission or change is needed.
  Refuse account/privacy/owner drift before creating the live probe target.
- Real user-initiated Microsoft sign-in/code exchange and fixed discovery/JWKS
  for the already configured public client/callback. Max2session exchange
  attempts; no account seeded or auth bypass. Temporary/email routes blocked;
  no SES/Resend send, credential rotation or SSMsecret read.
- One generated prefix `id01/next06-step3-<UUIDhex>/`, one create-only image
  PUTintent, maximum10MiB (selected source428492bytes). Only normal signed
  GET/PUT and actual adapterGET within this prefix;40adapter SDKoperations,
  300normalAPIrequests and20operator requests maximum, one create/one edit.
  Mutations never retried automatically; existing1000objects/RDSrows untouched.
- The local operator consumes the genuine API-issued signed URLs itself: exactly
  one HTTPSPUT of the fixed source photo and at most two HTTPSGETs of that same
  object. Only the exact bucket's regional/global S3host aliases and the generated
  run key/UUIDv4 are allowed. Require short-lived v4signature/Mumbai credential
  scope; deny userinfo, other hosts/ports/paths, ambiguous/encoded paths, redirects,
  proxies, extra headers or body bytes. No raw signed URL enters any receipt.
  Transfer counts are serialized and tracked separately from SDKcounts. Every
  download must match source size/SHA256 before returning bytes to browser.
  The browser makes no direct S3requests; no localhostCORS/IAM/policy edit.
- Only a fresh Unix-only local native cluster with separate restricted Identity/
  marketplace SCRAMroles and the installed real model. APIloopback8000 and
  front-endloopback5173, one process each,30minutesmaximum. Refuse busy ports.
  No Docker/global installs/model download, EC2/RDSstart or hosted deployment/
  resize/Terraform/DNS/shared-resource mutation.

Budget envelope USD1incremental, not a billing hard cap. No new cloud compute
charges; small S3request/transfer and up to10MiBretained object storage can incur
charges. Existing baseline/storage/credits/taxes not reconciled here. Prior
reviewed Mumbai S3price references are in cloud-price-evidence.json. No automatic
increase of budget/resources on failure. SDKconnect5s/read10s/no retry; browser
read polling<=25attempts per create/edit,2sdelay,10ssearch timeout; other requests
30stimeout. Record503while publication is pending; these are not NFRsamples.

## Evidence, stop and retention

Backend records only operation/status counts, synthetic source fingerprints,
current generation/part counts and exact probe keys; no private account rows,
credentials, assertions, cookies, signed URLs or source text in Git evidence.
The operator report is an untrusted browser annotation and cannot mark the
workflow passed. Backend pass additionally requires normal real sign-in200,
create201/edit200, confirm/delivery200, two distinct sources observed current
and two-part on successful Hybrid queries, and one final current listing.
The operator verifies actual delivered bytes against the source; browser automation
also hashes/decodes them. Neither mock HTTP nor a forged browser report can
substitute for the server transfer/SQLwitnesses.
Human confirmation is still needed; do not infer it from button output.

Stop on review/account/bucket/port drift, failed/uncertain mutation or bounds;
no policy repair, broader scope or retry. Close app pools/worker/model and verify
owned native cluster stopped; stop owned frontend. No cloud compute was started.
Retain the new probe object and private stopped local SQL until separately
approved scoped cleanup; never delete reference images. Local real account data
stays in its0700temporary directory, outside Git. Final DATA-READY remains false
until remaining required steps and real readiness/source/label/freeze gates pass.

## Preparation evidence

- step-03-search-operator-native-final.json: actual restricted SQL/auth role/
  model/worker startup; operator HTML200/exact photo bytes; normal API401without
  session; private session-table access denied; cluster stopped;0AWS/provider calls.
- Offline Node execution of the automatic driver completed using explicit mock
  HTTPresponses only; actual public CreateListingRequest/ListingReplacement
  validators accepted its generated mutation bodies. This proves client wiring,
  not a live workflow/auth/S3 result. Missing initial PYTHONPATH caused one local
  import refusal before execution; corrected invocation passed.
- Focused tests cover same-origin/loopback/body/CSP/static-resource boundaries,
  no normal API interception, no forged report pass, strict transfer URL/key/size/hash/attempt guards,
  real offline SDKpresign compatibility, create/edit/upload budgets,
  wrong-account rejection, current-source query witnesses and approval-before-SDK.
- Full checks/source hashes/secret scan are in step-03-search-vector-preparation-result.json.
