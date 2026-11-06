# ID-01 Step 14 — direct-API capability matrix

**Current disposition (2026-11-05):** Aditya directed ID-01 and Step 14 complete. The work log records that status. This page preserves the acceptance matrix and dated evidence pointers; it does not add new execution evidence.

## Scope and use

Step 14 defines Identity's regular/temporary authorization expectations across 47 Listings, Search, Conversations and Identity operations. The canonical requirements are in the [domain task list](../../../tasks/domain-task-list.md#id-01--implement-identity-eligibility-and-temporary-accounts). The table is a policy matrix, not a claim that every row has an automated receipt. Human verification and current completion status are recorded separately in the [work log](../../../status/work-log.md).

[Per-operation conditions and the original evidence mapping](capability-matrix.json) are a point-in-time record from 2026-10-28. Its `partial_local_execution_pending_human_verification` field describes that earlier checkpoint; it is not the current task status. Historical plan details and exact dated outcomes remain in Git history and the JSON receipts below.

## Expectations

`A` means allowed only with valid data, ownership/membership/visibility/state;
not an unconditional200. `D403` is active temporary class denial. `O` is own
upload only: an ordinary temporary actor has no upload-creation right; addressing
another actor's real intent must404. Do not fabricate temporary-owned uploads
or incorrectly expect blanket403 from confirmation/cancellation. `E` means an
allowed own-list read normally returns empty for a temporary actor. All listed
operations require real authentication: expired/revoked requests must401 with
valid request shapes before domain side effects. Hosted paths add `/api`.

| ID | Owner | Operation | Regular | Temporary | Existing evidence |
|---|---|---|---|---|---|
| M01 | listings | `GET /listings` | A | A | A6 |
| M02 | listings | `POST /listings/{listing_id}/conversations` | A | A | C1 |
| M03 | listings | `GET /catalogue` | A | A | A1, A2, A3 |
| M04 | listings | `POST /image-uploads` | A | D403 | A2, C1, A4 |
| M05 | listings | `POST /image-uploads/{upload_id}/confirm` | A | O | C1 |
| M06 | listings | `DELETE /image-uploads/{upload_id}` | A | O | No direct-session reference identified |
| M07 | listings | `GET /images/{image_id}/delivery` | A | A | No direct-session reference identified |
| M08 | listings | `POST /listings` | A | D403 | A2, C1 |
| M09 | listings | `GET /listings/{listing_id}` | A | A | No direct-session reference identified |
| M10 | listings | `GET /me/listings` | A | E | A1, A2, A3, A6 |
| M11 | listings | `PUT /listings/{listing_id}` | A | D403 | No direct-session reference identified |
| M12 | listings | `PUT /listings/{listing_id}/availability` | A | D403 | C1 |
| M13 | listings | `PUT /listings/{listing_id}/selection` | A | D403 | D2 |
| M14 | listings | `PUT /listings/{listing_id}/conversations/{conversation_id}/offer` | A | A | C1 |
| M15 | listings | `POST /listings/{listing_id}/conversations/{conversation_id}/offer-withdrawals` | A | A | C1 |
| M16 | search | `POST /wanted-requests/draft-matches` | A | A | No direct-session reference identified |
| M17 | search | `GET /wanted-requests` | A | A | A5, A6, C2 |
| M18 | search | `GET /me/wanted-requests` | A | A | A5, A6 |
| M19 | search | `POST /wanted-requests` | A | A | C2, A6 |
| M20 | search | `GET /wanted-requests/{request_id}` | A | A | No direct-session reference identified |
| M21 | search | `PATCH /wanted-requests/{request_id}` | A | A | No direct-session reference identified |
| M22 | search | `PUT /wanted-requests/{request_id}/availability` | A | A | No direct-session reference identified |
| M23 | search | `POST /wanted-requests/{request_id}/conversations` | A | D403 | C2 |
| M24 | search | `GET /me/saved-listings` | A | A | A5, A6, D4 |
| M25 | search | `PUT /me/saved-listings/{listing_id}` | A | A | A6, D4 |
| M26 | search | `DELETE /me/saved-listings/{listing_id}` | A | A | A6, D4 |
| M27 | conversations | `GET /conversations/{conversation_id}/contact-options` | A | A | C1, D1 |
| M28 | conversations | `POST /conversations/{conversation_id}/contact-preparations` | A | A | C1, D1 |
| M29 | conversations | `POST /conversations/{conversation_id}/messages` | A | A | C1, C2 |
| M30 | conversations | `POST /conversations/{conversation_id}/contact-shares` | A | A | D2 |
| M31 | conversations | `GET /conversations/{conversation_id}/entries` | A | A | C1, C2 |
| M32 | conversations | `GET /conversations/{conversation_id}/read-state` | A | A | C2 |
| M33 | conversations | `GET /me/conversation-key` | A | A | C3 |
| M34 | conversations | `PUT /conversations/{conversation_id}/read-state` | A | A | C2 |
| M35 | conversations | `GET /conversations` | A | A | C2, C3 |
| M36 | conversations | `GET /conversations/{conversation_id}` | A | A | C2 |
| M37 | conversations | `GET /conversations/{conversation_id}/offer` | A | A | C1 |
| M38 | conversations | `GET /conversations/{conversation_id}/keys` | A | A | C2 |
| M39 | conversations | `PUT /me/conversation-key` | A | A | C1, C3 |
| M40 | conversations | `GET /me/conversation-prekeys` | A | A | D3 |
| M41 | conversations | `POST /me/conversation-prekeys` | A | A | D3 |
| M42 | conversations | `POST /conversations/{conversation_id}/prekey-bundle` | A | A | D3 |
| M43 | identity | `GET /me` | A | A | A1, A2, E13 |
| M44 | identity | `PATCH /me/profile` | A | A | I1 |
| M45 | identity | `GET /me/contacts` | A | A | A1, I1, E13 |
| M46 | identity | `PUT /me/contacts/{contact_kind}` | A | A | A1, I1, E13 |
| M47 | identity | `DELETE /me/contacts/{contact_kind}` | A | A | C1, I1, E13 |

The JSON records per-operation conditions, specific missing cases and terminal
variants. `GET /me/listings` is permitted for temporary users; sale create/edit/
availability/selection remain denied. Temporary users can manage their Wanted
requests and participate in listing chats/offers, but cannot initiate Wanted
responses. Already copied encrypted shares and issued signed URLs retain their
reviewed independent lifetimes; source deletion/API denial does not erase copies.

## Evidence legend (source inspected; not rerun)

- **A1**: [test_application_composition.py](../../../../apps/api/tests/domains/identity/test_application_composition.py) `::test_real_cookie_enables_existing_listings_and_own_contact_routes`. Real regular cookie/catalogue/profile/contact flow; controlled signer/mail.
- **A2**: [test_application_composition.py](../../../../apps/api/tests/domains/identity/test_application_composition.py) `::test_temporary_cookie_does_not_authorize_seller_endpoints`. Real temporary cookie: catalogue/empty own-list read, create-upload/create-sale403.
- **A3**: [test_application_composition.py](../../../../apps/api/tests/domains/identity/test_application_composition.py) `::test_listing_routes_recheck_real_session_lifecycle`. Actual catalogue/own-list reads deny terminal regular sessions; not all Listings operations.
- **A4**: [test_application_composition.py](../../../../apps/api/tests/domains/identity/test_application_composition.py) `::test_untrusted_origin_and_csrf_cannot_mutate_listings`. Existing transport/CSRF rejection; not every mutation.
- **A5**: [test_application_composition.py](../../../../apps/api/tests/domains/identity/test_application_composition.py) `::test_real_session_reaches_accepted_search_routes`. Real regular/temporary Wanted/Saved empty-page reads only.
- **A6**: [test_application_composition.py](../../../../apps/api/tests/domains/identity/test_application_composition.py) `::test_marketplace_saved_and_wanted_reject_terminal_real_sessions`. Regular/temporary terminal reads and selected writes; not full endpoint matrix.
- **C1**: [test_conversation_identity_integration.py](../../../../apps/api/tests/test_conversation_identity_integration.py) `::test_signed_listing_publication_to_temporary_buyer_conversation`. Real cookie/SQL image-intent/listing/chat/offer/own-contact flow; image storage controlled; opaque synthetic envelopes do not prove encryption.
- **C2**: [test_conversation_identity_integration.py](../../../../apps/api/tests/test_conversation_identity_integration.py) `::test_signed_wanted_origin_to_messages_and_read_state`. Real Wanted regular/temporary author, regular response/temp response denial, member/nonmember and terminal message/read-state flows; opaque payloads.
- **C3**: [test_conversation_identity_integration.py](../../../../apps/api/tests/test_conversation_identity_integration.py) `::test_real_session_and_csrf_authorize_conversation_key_writes`. Real regular cookie/key registration/read/logout checks; not all cohorts/key operations.
- **I1**: [test_contacts_http.py](../../../../apps/api/tests/domains/identity/test_contacts_http.py) `::test_own_http_crud_security_and_no_session_disclosure`. Real Identity own-field HTTP checks; expand field/lifecycle/cross-domain combinations.
- **P1**: [test_capabilities_postgres.py](../../../../apps/api/tests/domains/identity/test_capabilities_postgres.py) `::test_regular_temporary_matrix_with_trusted_real_callers`. Policy-only real SQL with constructed trusted callers; not consumer HTTP evidence.
- **D1**: [test_conversation_contact_preparation.py](../../../../apps/api/tests/test_conversation_contact_preparation.py) `::test_real_own_contact_selection_no_writes_and_current_field_removal`. Real SQL/Identity contact boundary, synthetic request authentication; not real-cookie full matrix.
- **D2**: [test_conversation_contact_share_cleanup.py](../../../../apps/api/tests/test_conversation_contact_share_cleanup.py) `::test_offer_selection_and_contact_share_work_together_through_real_apis`. Real SQL/domain operations with synthetic request authentication; not full Identity-session proof.
- **D3**: [test_conversation_directory.py](../../../../apps/api/tests/test_conversation_directory.py) `::test_prekey_batches_atomic_retry_reservation_depletion_and_target_conflict`. Directory/prekey SQL/domain cases with synthetic callers; not full cookie matrix.
- **D4**: [test_saved_postgres.py](../../../../apps/api/tests/domains/search/test_saved_postgres.py). Real saved SQL/HTTP but explicit upstream Listing fixtures; not full real integration.
- **E13**: [closeout-review.json](../../../../docs/evaluation/identity/id-01-step-13/closeout-review.json). Human-accepted hosted Identity flows; not consumer-wide FR-03 matrix.

## Retained execution records

These files preserve the bounded historical plans and outcomes. They are evidence, not reusable approvals or current cloud state.

| Record | Contents |
| --- | --- |
| [Dependency reconciliation](dependency-reconciliation.json) | Sources and gaps observed during the original matrix preparation. |
| [Stopped configuration result](stopped-config-result.json) | Recorded stopped-state configuration outcome. |
| [Provisioning window results](provisioning-window-result.json), [retry result](provisioning-window-retry-result.json) | Historical role/provisioning attempts and resulting resource state. |
| [S3/Conversations live result](s3-conversations-live-result.json) | User-confirmed listing/image/conversation test outcome and narrow catalogue grant details. |
| [S3/Conversations teardown result](s3-conversations-teardown-result.json) | Recorded cleanup outcome. |
| [Catalogue grant plan](catalogue-lock-grant-plan.json) and [proposed Conversations grants](conversations-runtime.sql.proposed) | Narrow database permission artifacts and proposed SQL. |
| [Step 13 evidence](../id-01-step-13/README.md) | Hosted identity, email, HTTPS, retention and cleanup evidence. |

For any new runtime or cloud action, reread the owning task and current environment records, obtain the exact required approvals, and prepare a fresh reviewed plan. Do not infer current resource state or approval from these historical records.
