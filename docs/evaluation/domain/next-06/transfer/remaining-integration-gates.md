# NEXT-06 remaining integration and acceptance gates

The dataset-owned evidence checkpoint is human-verified. No further cloud action
is authorized by that verification. Preserve the existing dataset, vectors and
1,000 S3 images. Both EC2 and RDS were verified stopped at
2026-10-31 10:33:47 UTC; this is the last observation, not a fresh inventory.
Review stopped RDS by 2026-11-06 10:33:47 UTC before its possible seven-day automatic
restart. Retained storage and baseline resources can still incur charges.

| Remaining gate | Responsible scope | Required evidence |
|---|---|---|
| Accepted runtime/source | Deployment and domain owners | Exact accepted revision, real Identity configuration, reviewed Linux Hybrid image/model and host/task fit; existing t3.micro is not an approved Hybrid hosting plan. |
| Real normal workflow | Identity/Listings/deployment owners, Search for vectors | Controlled authenticated session; normal create/edit and automatic current-vector processing; owner/nonowner/anonymous/revoked-session image authorization and signed S3 delivery. Use separate owned mutation probe data and preserve reference corpus. |
| Upstream readiness | Identity/Listings owners | Accepted ID-READY and LI-CORE evidence/revisions; refresh recorded acceptance without treating missing status as missing implementation. |
| Final label envelope | Mohit/Search after prerequisites | Bind the unchanged22accepted judgments to accepted source, public contract and frozen manifest with actual human review metadata. Preserve unknown timestamps; no invented review time, new judgments or score-driven exclusions. Follow data/formats/query-labels.md. |
| Final freeze/publication | Mohit and independent peer | Review exact diff/source/labels/evidence and current required checks, explicit commit/push approvals and independent human PR approval. Final DATA-READY remains false until all required gates pass. |

## Receiving-owner evidence

- [Actual S3/RDS load](cloud-load-20261031/result.json):5,000users,1,000listings,
  1,000verified real-image objects,800discoverable listings.
- [Actual serving vectors](vector-production-20261031/result.json):1,000current
  generations/2,000parts, six production SQL engineering cases, source invariant.
- [Current native rebuild](dataset-current-native-rebuild.json) and
  [actual read-only cloud comparison](dataset-snapshot-20261031/result.json):
  identical logical vector and65index hashes, private access closed/resources stopped.
- [Unchanged accepted-label validation](dataset-label-evidence-check.json) and
  [consolidated candidate](dataset-evidence-candidate.json).
- [Hosting boundaries and exact owner handoff](dataset-evidence-plan.md).

No message has been sent to another contributor. No deployment, resize, additional
upload, deletion, database reset or scoring is part of this handoff.
