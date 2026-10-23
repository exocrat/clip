# Campus Marketplace

Campus Marketplace (CLIP: Campus Listing and Item Platform) is a planned private marketplace for the IISc community. It is intended to make it easier to find items for sale, publish wanted requests, and communicate with buyers and sellers.

The planned product includes identity checks, listings and images, search, saved listings, wanted requests, private conversations, offers, deliberate contact sharing, and email notifications. The platform will not verify payment, item quality, collection, delivery, or handover. The project also includes an evaluation of ECS-only and ECS-plus-Lambda deployments.

**Project status:** PD-00–PD-19, PRE-00, and DL-00 are recorded complete. This branch is implementing ID-01 toward ID-READY. Microsoft registration settings are human-confirmed; real SES application-role delivery, inbox receipt and owned test cleanup passed. Step2 production access/configuration review remains pending under approved staged progression. Step3 Identity schema hardening and disposable PostgreSQL upgrade/rollback checks passed locally and are human-verified. Step4 private Microsoft validation/account mapping passed local signed-token and real PostgreSQL checks; public login/session/UI integration and ID-READY acceptance remain pending. Step5 private OTP primitives and transactional challenge storage passed local gates and are human-verified; minimal request-marker lifetime retention is approved, while cleanup design and real public/provider integration remain pending. The newer Listings PR10 integration is deliberately deferred on this branch until later reconciliation with current main. See the [work log](docs/status/work-log.md) and [Step3 evidence](docs/evaluation/identity/id-01-step-3/README.md). Cloud snapshots are recorded in the [environment inventory](docs/environment/cloud-inventory.md); historical foundation evidence is in the [PD-19 handoff](docs/status/foundation-handoff.md) and [cloud checks](docs/evaluation/foundation/pd-16/README.md).

## Project documents

- [Product scope and requirements](docs/product/product-reference-and-architecture-decisions.md)
- [Project phases, tasks, owners, and dependencies](docs/tasks/project-task-index.md)
- [All canonical documents](docs/README.md)

## Contributing and setup

- [Contribution and review workflow](CONTRIBUTING.md)
- [Local foundation setup and troubleshooting](docs/environment/README.md#local-foundation-setup)
- [API-specific settings and tests](apps/api/README.md)
- [WSL first-session setup for Windows contributors](docs/environment/wsl-and-first-session.md)
- [Project command registry](docs/environment/commands.md) — exact commands, effects, and verification status.
