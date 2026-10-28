# Human browser and phone verification

This procedure makes the domain task list's browser checkpoints concrete. The
agent runs setup and automated checks; the human inspects and exercises the
visible result. Automated success does not establish human verification.

## At each visible feature increment

1. The agent starts the applicable services and gives the exact URL, current
   revision, safe synthetic account or explicitly labeled isolated mode, actions
   to try, and expected visible results. State which dependencies are real and
   which are test doubles. Do not ask the human to reconstruct setup commands.
2. The human opens the result on a desktop-sized viewport, tries the new action,
   and checks the relevant loading, empty, validation, denied/expired,
   unavailable, retry and error states that the agent has prepared safely.
3. Repeat at a narrow phone portrait size and landscape; use an intermediate
   tablet width when the layout changes there. Example inspection sizes are
   360 × 800, 390 × 844, 768 × 1024 and 1280 × 800 CSS pixels, not a promise of
   support for every device. Record the sizes actually checked. Look for clipped
   text, overlapping controls, unintended page-wide horizontal scrolling,
   unreachable actions, unreadable forms and controls that depend only on hover.
4. At device-dependent checkpoints, repeat on actual supported phone/browser
   combinations. Check the camera/gallery and file picker for images, and the
   on-screen keyboard for forms and the conversation composer. Record browser,
   OS/device and the selected support scope; emulation is not device evidence.
5. The human reports observations and explicitly verifies or requests changes.
   The agent records the checkpoint, result and verification in the work log,
   fixes within scope, and re-presents affected checks. An unavailable browser or
   device check remains pending. Preserve real integration and other acceptance
   gates; a synthetic demo does not complete them.

Perform this cycle when the first usable screen/action appears, after meaningful
user-visible increments, and again for the integrated journey. Preserve existing
numbered task order; these are checkpoints inside those steps.

## Firefox mobile layout inspection

1. Open the running app, currently `http://localhost:5173` for this workstation.
2. Press **Ctrl+Shift+M** on Windows/Linux, or **Cmd+Option+M** on macOS.
   Alternatively use Firefox menu → Browser Tools → Responsive Design Mode.
3. Set the width/height above the page (for example 390 × 844), or select a
   device preset. Resize between narrow and wide screens and rotate the viewport.
4. Browse and click the implemented flow inside that viewport. Touch simulation
   can help inspect interactions, but does not reproduce a physical phone.
5. Press the same shortcut or close the mode to return to normal browsing.

The tool changes viewport/device settings; selecting an iPhone preset does not
run Safari. It does not verify a phone camera, native picker, actual keyboard,
or measured mobile performance. See the official
[Firefox Responsive Design Mode guide](https://firefox-source-docs.mozilla.org/devtools-user/responsive_design_mode/).

An actual phone needs a reachable approved test URL: its `localhost` points to
the phone, not this developer's computer. Prepare the access method when needed;
do not silently change loopback bindings or expose services as part of a layout
check.

For Suraj's LI-02 Step 12, the website and API are deployed to ECS behind a
public load balancer. The laptop and phone open the same deployed URL; neither
device depends on a server or forwarding rule on the laptop. The public demo is
unauthenticated while running and uses only the fixed synthetic seller and
synthetic data. Step 12 uses the generated ALB HTTP hostname and exact CORS
origin; HTTPS is deferred until real integration. The actual phone check verifies the deployed website and listing
image flow; no separate camera/gallery acceptance gate is added here.

## LI-02 browser checkpoints

For the Step 9 local desktop review, the agent starts the built UI at
`http://127.0.0.1:5174/listings/new` using the explicit isolated Listings
browser command in the [command registry](commands.md#li-02-step-9--isolated-postgresql-browser-checkpoint).
That page uses a fixed synthetic seller, a separate real local PostgreSQL
container, and temporary in-memory photo storage; its banner states that no AWS
is used. The agent first checks uploads, retry, saved rows, galleries and
responsive layouts in a desktop browser. Human review then checks the visible
experience. The loopback address works on this computer only; it does not let a
phone reach the server.

Use controlled synthetic item photos. Review existing-image selection,
progress/retry, rejection, gallery/file-picker behavior and previews in the
local desktop browser and responsive viewport checks. The actual mobile website
check occurs only at Step 12 after deployment; verify the deployed site and
listing image flow are usable on the selected supported phone/browser. It does
not add a separate camera-capture acceptance gate. Captured files still obey
the approved image type/size/count rules; unsupported files need a clear
rejection or a separately reviewed conversion policy.

Do not require a particular HTML attribute or camera API before implementation
review. Browser capture support varies; ordinary file selection must remain
available. [MDN's capture reference](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/capture)
documents the platform limitation. Step 9's local checks use no AWS. At Step 12,
use the approved reachable URL for the deployed mobile website check; isolated
browser checks remain separate from the real RDS/S3 rehearsal.
