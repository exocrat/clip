# CLIP Product Requirements

This is a readable summary of the original [submitted PRD](docs/source/ICC_Project_PRD_FINAL.pdf), not a replacement for it. The [product reference](docs/product/product-reference-and-architecture-decisions.md) records later accepted clarifications; the [work log](docs/status/work-log.md) records implementation and verification status. Requirements below are goals, not a claim that every feature or measurement has been accepted.

## Problem and users

IISc students currently use chronological messaging groups to exchange used items, making active offers hard to rediscover and compare. CLIP gives the IISc community a structured marketplace for discovery, communication, offers, and seller-controlled availability. Primary users are buyers, sellers, incoming students using temporary accounts, and the team operating the service.

## Intended user journeys

1. An eligible user browses or searches items, saves a listing, contacts the seller, and optionally makes an offer.
2. A seller publishes an item with images, manages conversations and offers, optionally selects a buyer, and marks the item unavailable.
3. A user drafts a wanted request and sees possible sale matches before publishing it. Open requests can also be discovered; an eligible regular member can contact the requester privately.
4. An incoming student verifies a personal email for a restricted temporary account that expires after 14 days.

## Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | Validate signed Microsoft identity tokens and an approved IISc account identifier for regular access. |
| FR-02 | Support email-verified temporary accounts that expire after 14 days and cannot self-renew. |
| FR-03 | Permit temporary users to browse, search, save, create wanted requests, start listing conversations, and offer; prohibit sale listing creation. The later wanted-response decision restricts responding to wanted requests to regular users. |
| FR-04 | Let eligible regular users create listings with title, description, category, condition, price including zero, negotiability, availability, and at least one image. The original PRD specifies a pickup area; a later accepted clarification makes it optional. |
| FR-05 | Restrict editing and authoritative availability changes to the owner; exclude unavailable listings from discovery. |
| FR-06 | Provide paginated browsing of available listings to eligible users. |
| FR-07 | Search titles and descriptions, filter by category, price, condition and negotiability, and sort by recency or price. |
| FR-08 | Create and manage wanted requests with optional budget and show potential sale matches before submission. |
| FR-09 | Save and unsave listings; preserve a saved reference when the listing becomes unavailable where permitted. |
| FR-10 | Provide at most one private conversation per buyer/listing pair, authorized message retrieval, ordering, and ciphertext storage. |
| FR-11 | Support structured offers with amount, optional note, timestamp, and status, including appropriate revisions and withdrawal. |
| FR-12 | Allow participants to deliberately share only selected phone, email, or UPI details in a conversation. |
| FR-13 | Send asynchronous event emails and unread reminders, suppress reminders when read, and keep message success independent of email delivery. |
| FR-14 | Store images in object storage and reference them from listing records; handle upload and partial failures. |
| FR-15 | Allow sellers to mark listings unavailable without representing payment, quality, collection, delivery, or handover as verified. |
| FR-16 | Encrypt private messages on clients; only participants decrypt, while the server stores and relays ciphertext. Server recovery of lost client keys is not provided; the original MVP targets one active browser device per user. |
| FR-17 | Flag listings over a configurable price threshold or in phone/laptop categories and show an optional, unverified seller proof-of-purchase declaration. |

## Non-functional targets

Use at least 1,000 synthetic listings and 5,000 synthetic users for the reference performance workload; runs last at least five minutes after warm-up and distinguish cold and warm behavior where applicable.

| ID | Original target |
|---|---|
| NFR-01 | At 20 requests/s, at least 95% of successful browse requests finish within 1 second, excluding image-body transfer. |
| NFR-02 | At 10 requests/s, at least 95% of indexed search requests finish within 1 second on the reference data. |
| NFR-03 | During a five-minute 50 requests/s peak, at least 95% of requests succeed, excluding deliberately rate-limited abusive requests. |
| NFR-04 | At least 80% Success@5 on at least 20 human-labeled representative queries. |
| NFR-05 | At least 95% of messages become visible to a recipient with the conversation open within 5 seconds under normal workload. |
| NFR-06 | With at least two healthy runtimes configured, restore healthy serving capacity within 240 seconds after forced loss of one. |
| NFR-07 | Restore the latest managed database backup to a usable test database within 30 minutes. |
| NFR-08 | Keep total implementation and evaluation cloud spend below USD 200; declare caps and duration before each load experiment. |

Measurement details and evidence are tracked in the [NFR design](docs/evaluation/nfr/measurement-design.md), not inferred from local tests.

## Architecture and experiment

The baseline is a responsive React/TypeScript client, FastAPI REST service, PostgreSQL for authoritative state and indexed search, and S3 for images. ECS is the baseline API runtime; Lambda supports asynchronous work and the comparison. Conversations use HTTPS, client-held keys, and polling through the normal API. See [dev.md](dev.md) for the implemented repository layout.

The primary experiment compares ECS-only with ECS plus Lambda for a fixed set of read-heavy endpoints while keeping writes on ECS and the dataset and workload comparable. Record latency percentiles, successful throughput, failures, cold starts, resource behavior, and cost; conclusions apply to the measured configuration only. See the [experiment plan](docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md).

## Exclusions and optional work

Payment processing or verification, delivery coordination, ratings, auctions, partial quantity sales, atomic swaps, native mobile apps, offline operation, multilingual UI, WhatsApp listing creation, automated pricing, comprehensive moderation, and active multi-region serving are outside the MVP. Weekly wanted digests, match alerts, image-aware search, and additional comparisons are optional and need their own scope and approval.
