# Local two-browser encrypted chat checkpoint

CN-01 Steps 5–9 and CN-02 seller-selection checkpoint, isolated browser
verification only. Real PostgreSQL, the normal Listings and Conversations
routers, built React UI, OpenE2EE 13.0.0 and IndexedDB are used. Request
authentication is **two fixed synthetic server identities**, not real Identity
sessions/Microsoft sign-in. Identity eligibility uses real SQL for the synthetic
accounts. This does not accept ID-READY, CN-CORE, LI-CORE, FR-10/16 or NFR-05.

## Agent setup

Use the existing branch/locked environment and local Unix-socket Docker with
PostgreSQL18.6/dbmate2.36 images. No extra packages, AWS account or provider is
needed. From the root, with Node24/npm11 on PATH:

```bash
npm run build
CLIP_ENVIRONMENT=test uv run --locked python scripts/conversation_browser.py --isolated-conversation-browser --check-only
CLIP_ENVIRONMENT=test uv run --locked python scripts/conversation_browser.py --isolated-conversation-browser
```

The agent starts the last command for the human; do not start another copy.
The opt-in refuses production/default environments and ambient database/provider
settings. It accepts no existing target, authentication selector or host/port
override. The helper creates one new tmpfs PostgreSQL container with no network,
uses its private local Unix socket and checked-in migrations, then seeds one
synthetic listing and creates its conversation through the actual Conversations
operation. Listings selection uses its actual PostgreSQL store and actual
Conversations participant-check interface. The check-only run selects and clears
the synthetic buyer to verify the complete server-side path, then leaves the
browser fixture unselected. No messages/keys/ciphertext are preloaded. Two separate bounded pools
serve the normal bundle on `127.0.0.1:5273` (A, seller) and `:5274` (B, buyer).
Each side enforces its exact host/origin, a loopback peer and its own transient
write token. Browser IDs/headers cannot switch the fixed actor. No test-auth route
or normal application configuration enables this harness; scripts/tests are
excluded from the production image.

`--check-only` checks HTTP/SQL access, seller-only listing reads, exact-thread
selection and clearing, and guards without opening listeners. It does not
execute browser JavaScript, encryption or IndexedDB. Normal operation
ends after 30 minutes (explicit `--seconds` accepts60–3600) or Ctrl+C. Both
listeners/pools stop and only the helper's own container/data are removed. Existing
Docker resources, databases and browser storage are not deleted. A setup failure
stops rather than resetting an existing target. No live providers or email run.

## Human walkthrough

Use two desktop browsers/profiles if available. The distinct origins also isolate
storage in a single browser, but record that as a two-origin rather than a
cross-browser result. Always use the exact `127.0.0.1` URLs, not `localhost`.

1. Open [A's inbox](http://127.0.0.1:5273/my/conversations) and
   [B's inbox](http://127.0.0.1:5274/my/conversations). Check the prominent
   **LOCAL E2EE TEST — synthetic data only** banner on each side. Do not use
   `?demo=conversations`: that older presentation demo does not encrypt.
2. Open the one test conversation on both sides. Read and acknowledge the actual
   key-loss warning on each side to register its own browser key. The first side
   may initially report that the peer key is unavailable until the other side
   registers. After both register, use the displayed refresh/retry action on the
   first side. Never clear browser storage to work around a normal error.
3. Before sending messages, confirm A (seller) sees **Select this buyer** in the
   Sale Listing conversation while B (buyer) does not. The fixture has no offer;
   A can still select B. Click it and confirm the buyer is selected and the
   listing becomes unavailable (while its date window and chat remain intact).
   This does not accept an offer, reserve the item or confirm payment/handover.
4. Send a made-up message from A to B, then reply from B. Check both sender and
   recipient can read the text. The UI must not offer a plaintext fallback. Any
   key/decryption/send error is a finding, not an accepted outcome.
5. Reload both pages and close/reopen one tab while this server stays running.
   The same browser/profile/origin should retain keys and readable history.
   This checks a normal reload, not resistance to storage eviction or a backup.
6. Leave B at its inbox, send from A, and check B shows unread activity after
   refreshing the inbox. Open B's thread and display the message; return to its
   inbox and refresh. The badge should clear only after display acknowledgement.
   Reading/polling alone must not acknowledge a message.
7. Optionally test a failed send using the browser's offline control, then restore
   connectivity and use Retry. Expect no duplicated message. Do not enter real
   message content or export network bodies, ciphertext or key material.
8. Test Logout last: its fixed side must lose API/chat access and clear private
   UI. There is deliberately no test login/identity-switch endpoint. Restarting
   this harness creates a different fresh fixture and loses its old server data;
   it is not a persistence or recovery procedure. Cross-account switching remains
   separately covered by UI tests and pending real-session browser integration.

Report browser/version, normal/private profile, the checks actually attempted,
and any failure. Also inspect desktop and narrow portrait/landscape layouts.
Physical-phone keyboard verification remains pending: the intentionally
loopback-only setup is not a LAN/public phone endpoint. Do not expose it on
`0.0.0.0` to bypass this restriction.

Do not clear site data during the persistence check. If deliberately testing key
loss later, use only these test origins and record the destructive test separately.
Browser-local keys/history are not backed up and this harness never recovers them.
No deployed latency result or real Identity sign-in acceptance is claimed.
