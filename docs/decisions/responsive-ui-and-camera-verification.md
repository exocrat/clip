# Responsive UI, phone camera selection and human browser checkpoints

**Date:** 2026-10-20

**Origin:** Suraj's Listings preparation before LI-01; clarification of LI-02
and the shared frontend verification procedure.

## Question

How should phone/desktop usability, camera/gallery selection and frequent human
inspection be made explicit before domain frontend implementation?

## Selected choice

The responsive web requirement applies to every domain, including Conversations,
offers and contact sharing. Add named human browser checkpoints inside existing
UI steps, starting with the first usable increment and repeating as meaningful
visible behavior arrives. The agent supplies setup, URL, actions and expected
results; the human opens and exercises desktop and mobile layouts and verifies
the result before the checkpoint advances.

For LI-02, Suraj clarified on 2026-10-22 that human mobile website verification
belongs at Step 12 after the isolated deployment. Step 9 remains a local desktop
and responsive-viewport review; it does not require a physical-phone checkpoint.
The Step 12 mobile check covers the deployed website's usability. It adds no
separate camera-specific acceptance gate.

On 2026-10-22, Suraj verified that the Step 12 demo is served by ECS and reached
through one public URL from both laptop and phone. The running demo is
unauthenticated but accepts only synthetic data, caps the isolated test profile
at ten listings, and has an easy start/stop lifecycle that removes LI-02-owned
runtime resources and test data. The lifecycle preserves shared RDS, VPC, NAT,
and other domains' resources. Step 12 therefore does not use laptop hosting,
SSM browser forwarding, Wi-Fi allowlists, or WSL port forwarding.

On 2026-10-22, Suraj chose the generated ALB HTTP hostname for this isolated
synthetic-data rehearsal and deferred HTTPS/domain setup until real integration.
The app accepts no real personal data or photos in this public test profile.
The start/stop workflow records shared RDS and ECS capacity state and restores
it only when doing so will not interrupt another shared workload.

LI-02 must support choosing existing phone images and taking a photo on supported
phone browsers, with cancellation/error handling and ordinary file selection as
a fallback and on computers. Existing image limits remain in force. Record the
supported browser/device scope before feature acceptance. The human Step 12
phone check verifies that the deployed website and listing image flow are usable
on mobile; it does not require a separate camera/gallery acceptance result.

Detailed checks live in the [domain task list](../tasks/domain-task-list.md) and
[browser procedure](../environment/browser-verification.md).

## Rationale

Passing automated foundation checks does not prove that a person can use a new
screen on their phone. Early human checkpoints expose layout and interaction
problems while the feature is still being built.

## Implications

All frontend owners follow these checkpoints. B implements camera/gallery
selection in LI-02; A/C/D review affected shared presentation and their own flows.
This clarification adds no HTTP operation, cloud resource, native application,
image-format expansion or selected camera library. Normal shared-owner review,
PR and exact merge gates still apply.

## Approver

Suraj (B), explicit instruction to add camera/responsive requirements and frequent
human browser verification. The corresponding task acceptance is recorded in the
work log; future features still follow these checkpoints.

## Supersedes

None; makes the existing responsive requirement testable and adds the explicit
phone-camera selection requirement without changing the submitted PRD.
