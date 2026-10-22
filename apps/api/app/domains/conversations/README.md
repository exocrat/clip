# Conversations domain

Owner: D — Rahul for CN-01/CN-02; A — Aditya owns CN-03 notifications, with D reviewing producer/read-state integration. Required implementation belongs to the [domain task list](../../../../../docs/tasks/domain-task-list.md), after the required foundation and contract gates.

`origin_retirement.py` currently implements only the internal `get_origin_activity` and `mark_origin_retired` database operations. It is tested directly, but is not wired by `main.py` or exposed as a route. It does not delete content or claim real Listings/Search integration. The future `notifications/` subtree is reserved for A; other conversation/offer implementation remains D-owned. Shared technical primitives belong in `app.core`; cross-domain calls use reviewed public interfaces. Message APIs, encryption, notification delivery, and the rest of the Conversations provider remain unimplemented.
