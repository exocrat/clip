# Campus Marketplace

Campus Marketplace (CLIP: Campus Listing and Item Platform) is a planned private marketplace for the IISc community. It is intended to make it easier to find items for sale, publish wanted requests, and communicate with buyers and sellers.

The planned product includes identity checks, listings and images, search, saved listings, wanted requests, private conversations, offers, deliberate contact sharing, and email notifications. The platform will not verify payment, item quality, collection, delivery, or handover. The project also includes an evaluation of ECS-only and ECS-plus-Lambda deployments.

**Project status:** PD-00–PD-19, PRE-00, and DL-00 are recorded complete. ID-01 is in progress toward ID-READY: Step 1 is verified and Step 2 provider setup is partial. Microsoft registration settings are human-confirmed; the SES sender domain is verified, while an offline-tested sandbox email adapter is prepared; production access, controlled delivery, runtime permissions, and authentication implementation remain pending. See the [current work log](docs/status/work-log.md) for checkpoints and evidence. A minimal local API provides process health, typed configuration, and tests. Private cloud API-health and restricted database checks have passed; compute is currently shut down. Marketplace features and performance/NFR results remain unimplemented/unmeasured. See the [PD-19 foundation handoff](docs/status/foundation-handoff.md) and [cloud foundation evidence](docs/evaluation/foundation/pd-16/README.md).

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
