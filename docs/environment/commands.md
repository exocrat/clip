# Runtime Command Registry

**Canonical path:** `docs/environment/commands.md`

This is a supplied planning template, not executable tooling or proof of implementation. PD-03 initializes it, and each command-creating task populates exact spellings/arguments/script paths and verifies safe behavior. The normal front door is root Makefile, unless PD-02 explicitly approves an equivalent and records actual mappings. Root README/CONTRIBUTING/CI must match this registry after PRE-00.

For EACH command record: creator task, exact invocation and required inputs, supported shell/runtime, target/environment, effects and destructive/billable behavior, prerequisite milestone, expected output/exit status, failure/recovery, tests/evidence. Commands must reject unspecified or wrong targets rather than guessing an AWS account/region/database.

| Required command outcome | Creator | Current state |
|---|---|---|
| Install/setup | PD-02/04/07/13 | Not implemented; exact command resolved there |
| Local start/stop/readiness | PD-05/07/08/13 | Not implemented |
| Local migration/status/reset and small seed | PD-08/13 | Not implemented; reset local-only and explicit |
| Generator framework/tests | PD-09 | Not implemented |
| Final reference generate/load/validate/fingerprint | SE-01/DATA-READY | Not implemented; requires domain schemas/configuration |
| Python format and non-mutating pinned Black check | PD-04 | Not implemented |
| Test/lint/type/build/aggregate CI-equivalent | PD-07/12/13 | Not implemented |
| Contract regenerate/stale-check | PD-11/DL-00 | Not implemented |
| Terraform static format/validate (no remote state mutation) | PD-15 | Not implemented |
| Plan/apply/build-release/deploy/verify/rollback/teardown | PD-15/16; domain/EXP additions | Not implemented; gated actions separate from local/CI check |
| Search evaluator/load workload/NFR manifests | SE-01 | Not implemented |
| Two-client chat/read-state/latency measurement | CN-01/CN-03 | Not implemented |
| Integrated peak/runtime-loss/DB-restore checks | INT-01 | Not implemented |
| Mixed Lambda package/routing/parity/deploy/workloads/analysis | EXP-02/03–08 | Not implemented |
| Final regression/export/demo/package verification | CLOSE-00 | Not implemented |

An absent command assigned to the selected creation step is an expected output; the agent creates/registers/tests it. An absent prerequisite or uncertain expected effect blocks the dependent action and requires a question. No cloud operation belongs in the generic local/CI aggregate target.

## Workstation and stub command registration

The setup guide contains one-time agent-access/clone commands, not implemented application targets. BOOT-00 records actual Linux paths/agent availability; PD-02/13 freeze the verified development toolchain and application commands. PD-10/DL-00/domain owners register explicit test-double scenarios and real integration commands with distinct names/modes. No deployed command may default to fake auth/storage/notification/domain providers; startup validation rejects them. Stub tests never share a label or result classification with cloud/NFR runs.
