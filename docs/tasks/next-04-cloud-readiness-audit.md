# NEXT-04 read-only deployment audit — 2026-10-29

Target: `https://clip-iisc.site`, with Notifications excluded from this delivery.
This is an audit and preparation plan, not authorization to deploy, migrate,
change IAM/DNS, send email or incur paid usage. Current observations and prior
receipts are linked from the [cloud inventory](../environment/cloud-inventory.md).

## Current observations and blockers

- The renewed `surajs2` profile identifies non-root user `surajs2` in account
  `335523638354`, region `ap-south-1`. SES reports production access and sending
  enabled. Historical Step13 evidence records Microsoft sign-in, temporary-account
  registration/reset and inbox receipt, HTTPS and secure-cookie checks; these
  do not establish the present hosted application is running.
- Shared API task revision 10 has desired/running/pending zero; its ASG has zero
  instances and the private RDS instance is stopped. The task explicitly enables
  the Identity **test** profile and dual email; Identity's source currently
  restricts the real senders to controlled recipients and refuses production
  startup. Suraj deferred the broader SES/Identity production source change.
- The API task role's inline policy permits scoped SES, three fixed Identity SSM
  references and the ID-01 S3 object prefix; its SES sender condition includes
  `verify@clip-iisc.site`. Effective permissions and the current private email
  route preference were not tested or read. The image bucket blocks public access,
  its bucket policy is nonpublic, and its CORS permits GET/HEAD/PUT only from
  `https://clip-iisc.site`.
- The repository has 29 SQL migrations. The Identity operator runner and reviewed
  test fixtures pin a 23-file candidate and deliberately reject an expanded chain;
  the earlier 17-file live package still requires its separate owner review.
  Category and Handle changes have only disposable local migration checks.
  A 29-file exact target/package and data-preserving upgrade plan are needed.
  Conversations also needs reviewed Identity schema usage and `SELECT` on the
  safe `identity.participant_profiles` view. That grant was exercised only in a
  disposable fixture, not applied to the shared database. Existing catalogue
  lock grants and their guarded restoration need to be preserved and checked
  against the actual selected migration head.
- Task revision 10 disables Hybrid search and its worker. Source defaults product
  search to Hybrid and combines eligible keyword and semantic matches. Listing
  inserts and text edits enqueue embedding generations for active pipelines, but
  a real helper/model, serving pipeline, worker, runtime grants and vector flow
  are still needed and have no positive hosted pass.
- ACM reports an issued certificate for the target domain. Google and Cloudflare
  public DNS returned no apex A record; public NS records point to Spaceship
  nameservers. Route53 has no exact hosted zone in the project account. The
  target did not resolve from this environment, and IISc DNS was not checked.
  A supported HTTPS ingress, exact trusted proxy headers, certificate binding and
  DNS mapping still need a reviewed design and hosted verification.
- The shared NAT gateway remains available and can incur charges. No `clip`
  EventBridge rules were returned; this alone does not establish that all
  schedulers or retained resources have been inventoried. Current Terraform
  state and drift, budget/headroom and retention scheduling remain unverified.

## Ordered plan for a future approved deployment

1. Finish the integrated source review and pinned local/CI checks. Have affected
   owners review Identity, Listings/images, Search and Conversations, including
   the participant projection and the exact migration order. Independently review
   the current PR revision. Resolve the deferred general-recipient Identity/email
   path before claiming a generally usable hosted marketplace.
2. As the authorized operator, refresh account, resource and Terraform state
   read-only; compare task revision, image digest, roles, secret *references*,
   networking and retained resources with source. Confirm remaining budget,
   capacity, resource ownership, stop deadlines and cleanup. Do not expose or
   print secret values. Reconcile any drift in an exact reviewable plan.
3. Prepare a checksum-pinned migration and grant package for the actual database
   baseline, including data preservation, backup/rollback, exact principals and
   catalogue and participant-view privileges. Obtain the recorded Identity owner
   review and separate approval for any shared database migration or grant.
4. Prepare the immutable AMD64 application image and Search-owned pinned model,
   helper, worker and pipeline preparation/queue/activation plan. Include
   least-privilege runtime access and prove a newly created and edited listing
   generates current vectors through the normal workflow; do not copy vectors.
5. Prepare an exact HTTPS ingress and trusted-proxy plan for the domain, preserving
   the ACM validation record and avoiding the previously rejected NLB assumption.
   Coordinate DNS with its actual operator and recheck public and IISc resolution.
   Configure exact browser origin, secure cookies, CSRF and forwarded-header trust.
6. Verify the selected Identity/email route and role scopes, private image bucket,
   prefix and CORS against the exact runtime. Review any SES/SSM/IAM changes and
   approve real email separately. Set an explicit resource/cost cap, start/stop
   sequence, retention cadence, deadline and cleanup ownership before starting.
7. Only after each required action has separate approval, deploy and perform real
   hosted sign-in, approved email, upload/confirm/display, listing create/edit and
   availability, Hybrid search and automatic vectors, Wanted/Saved, conversations,
   offers, selection and encrypted contact sharing. Test denials as well as
   successes; then conduct the human desktop/phone walkthrough. Record exact
   revisions, costs and post-stop retained resources. Until those checks pass,
   the target is not production-ready.
