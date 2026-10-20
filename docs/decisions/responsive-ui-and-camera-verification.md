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

LI-02 must support choosing existing phone images and taking a photo on supported
phone browsers, with cancellation/error handling and ordinary file selection as
a fallback and on computers. Existing image limits remain in force. Record the
supported browser/device scope before feature acceptance and verify actual-phone
camera/gallery behavior, not only desktop responsive-mode simulation.

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

Suraj (B), explicit instruction in this session to add the camera/responsive
requirements and frequent human browser verification. Shared publication and
affected-owner review remain pending.

## Supersedes

None; makes the existing responsive requirement testable and adds the explicit
phone-camera selection requirement without changing the submitted PRD.
