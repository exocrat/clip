# Identity domain placeholder

Owner: A — Aditya. Required feature implementation belongs to ID-01 in the [domain task list](../../../../../docs/tasks/domain-task-list.md), after the required foundation and contract gates. Step 2 now supplies an isolated sandbox SES transport in `email.py`; authentication, account, capability and contact implementation remain pending.

Identity owns its authentication/capability/contact behavior. Shared technical primitives belong in `app.core`. Other domains must use reviewed public interfaces rather than importing private implementation or reading private tables. `public.py` contains the generated reviewed DL-00 declarations. The sandbox transport is private to Identity and introduces no routes, schemas or authorization shortcuts. See the [provider setup](../../../../../docs/environment/identity-provider-setup.md) for configuration and pending real checks.

`email_smoke.py` is a separately gated one-shot ECS command that exercises
`email.py` using the real application task role. It is not wired to an HTTP route
or normal API startup. It sends at most one fixed synthetic message, only in
explicit approved test mode, and emits no recipient/content/credential data.
