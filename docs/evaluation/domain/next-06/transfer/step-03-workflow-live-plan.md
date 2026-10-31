# NEXT-06 Step3 — real browser create/edit/image/vector check

This is still Step3. Its bulk data/media load is already verified; this checkpoint
checks ordinary authenticated creation/editing and automatic vector production.
No final labels/freeze step advances until the result is human-verified.

## Execution and target

Backend command

`CLIP_ENVIRONMENT=test .venv/bin/python -m scripts.evaluation.reference_workflow_local --approved-live-local --seconds 1800`

Frontend: `PATH="$PWD/.tools/node/bin:$PATH" VITE_MICROSOFT_SIGN_IN_ENABLED=true .tools/node/bin/npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`

Use browser **http://localhost:5173/sign-in**, the already registered real Microsoft
SPA callback origin. API127.0.0.1:8000; one process each,30minute API limit.
Existing native PG18.6/dbmate and installed Python3.13.12/pinned model only.
No Docker/global installation/new model download, RDS/EC2start, hosted deployment,
resize, Terraform, DNS or public listener. Frontend dependencies restored only
inside this repository; typecheck/build passed with real sign-in enabled.

The new private Unix-only cluster gets canonical29schema and its own
clip_test_identity database, separate restricted Identity/marketplace roles with
actual SCRAMauthentication. Fresh local crypto keys stay in memory and apply only
to this new DB. Real IdentitySessions/MicrosoftKeys/MicrosoftTokenValidator,
cookie/CSRF handlers, actual app/service/store/S3adapter, model and background
worker are used; no fake caller, provider signer, copied session or bulk owner.
No SSMvalues needed: existing cloud DB URLs/authentication keys/email keys are
not read. No account is seeded; the human signs in normally.

## Exact external approval scope

Non-root IAMprofilemohitmahapa1/account335523638354/ap-south-1 only.
The six metadata reads verify STS identity and exact bucket ownership HEAD, public-access
block, policy-status, encryption and CORS for
clip-test-listings-images-ap-south-1-id01. Require all public access blocks enabled.
Default encryption must be AES256. Existing CORS must permit the exact origin
http://localhost:5173 with GET/PUT and content-type/if-none-match. If absent, refuse before local live DB or
S3objects. Do not change CORS/IAM/policy, widen origins or use another bucket.

Real Microsoft browser authorization/code exchange and server discovery/JWKS/
token signature/nonce validation for the user's controlled IISc account are
selected. Credentials/tokens stay in browser/provider/auth memory, never chat,
logs or Git. Microsoft sign-in only; temporary/email routes and all other
unselected mutations blocked; no SES/Resend send or secret/key read.

New prefix **id01/next06-step3-<one UUIDhex>/**, generated once after preflight.
At most two distinct normal image PUTintents, each<=10MiB under existing contract,
create-only if-none-match,40adapter SDKoperations maximum and300APIrequests.
Only actual GET and signed GET/PUT within this prefix; all other bucket/key/
operation/deletion rejected. Browser uses ordinary5minute signed URLs; direct
browser traffic/reuse is not a hard SDKcounter or billing cap. Do not repeatedly
refresh/download. Existing1,000reference objects and all RDSrows untouched.

One normal listing creation attempt, at most two edit attempts; failed attempts
consume the limit rather than retrying uncertain writes automatically. Low-price
synthetic listing text/photo only. Real account profile/nonce/session data exists
only in new local private SQL; max2controlled sign-ins/accounts selected. No
real contacts/messages/other feature workload needed. Local roles have no cloud
rights; selected AWSsession signs only the fixed new S3prefix and is restored on
exit. SDK5sconnect/10sread/no automatic retry; model/worker defaults unchanged.

Budget envelope **USD1 incremental**, not a hard billing cap or measured bill.
No new cloud compute allocation/start; small S3requests/transfers and up to20MiB
retained probe storage may incur charges. Existing baseline/storage excluded.
No account upgrade or automatic expansion. Same recorded Mumbai request/storage
price sources: cloud-price-evidence.json. Charges/credits/network/tax are not
claimed reconciled here.

Stop on identity/source/privacy/CORS/port drift, unknown failure, exhausted budget
or user stop; no repair/retry/extra permission in this window. On normal stop or
failure, close real pools/model/worker and stop/verify the owned native cluster;
stop owned frontend. No shared cloud resource was started, so no EC2/RDScleanup.
Retain new probe objects and stopped private local SQL for this checkpoint;
list exact probe keys in aggregate receipt. Their deletion needs separate scoped
cleanup approval. Never remove the1,000reference images. No secret or real-account
row/body/token is copied into Git; only aggregate statuses/counts/source hashes.

## Human browser actions after successful startup

1. Sign in normally using IISc Microsoft. Set a unique local Handle if prompted.
2. Create one available listing: title **Step3 Android smartphone**, description
   **Synthetic phone used to verify normal search vector publication**, category
   Mobile Phones, condition Good, price INR500. Upload
   `/Users/mohitmahapatra/Desktop/clip-dataset-images/mobile_phone/android-smartphone.jpg`.
   Verify successful publish and the real photo displayed.
3. Wait a few seconds, then search **smartphone**. The default Hybrid request must
   succeed and show this listing. Do this before editing: the witness must see
   the first source's current two-part vectors. No manual vector CLI is used.
4. Edit that same listing: change title to **Step3 Android smartphone updated**
   and description to **Updated synthetic phone description for automatic vector refresh**.
   Preserve its image; save once. Wait a few seconds and search **smartphone**
   again; verify successful result and updated detail/photo.
5. Report what worked/failed; stop the API so aggregate HTTP/SQLevidence is
   finalized (or let the30min timer stop it). Agent verifies processes/model/DB
   stopped and retains the safe result. Do not paste tokens/passwords/cookies.

Pass requires real sign-in200, upload/confirm, create201/edit200, delivery200 and
successful Hybrid queries on two distinct current source fingerprints with two
parts each. Final owned dataset has one listing and its current vectors. Human
photo display and browser behavior confirmation remain required; an HTTPcounter
alone cannot attest what the human saw. This does not claim the entire Identity/
Listings capability matrix, hostedLinux performance or an NFR result.

## Local preparation evidence

step-03-workflow-native-result.json proves actual restricted roles/private-table
denial, supported empty serving pipeline, real384dim inference and normal worker
startup with stopped native cleanup. Real sign-in/S3/create/edit flags remain
false until live execution and human verification. Two initial adapter row-format
failures are preserved separately; both stopped/no AWS; corrected native run passes.
