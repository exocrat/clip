# DEC-WEB-01 — Minimal web build tooling

**Date:** 2026-10-17

## Question
Which build setup implements PD-07 Step 1 within the selected React/TypeScript,
Node 24 LTS, npm, and single-root-manifest boundary?

## Options considered
- Vite with its React plugin: a small local development/build path for the
  existing separate FastAPI backend.
- A React framework with server rendering or additional server responsibilities:
  introduces application/runtime decisions the current foundation does not need.

## Selected choice
Use Vite 8.3.4, its React plugin 6.1.2, React/React DOM 19.3.1, TypeScript 7.0.2,
and React type declarations 19.3.0. Exact direct versions are in root
`package.json`; all resolved dependencies are recorded in the single root
`package-lock.json`. Node 24.22.0 and bundled npm 11.19.1 are the first verified
local runtime. Runtime version ranges remain within the selected release lines.

## Rationale
This keeps the technical client mount point independent of unimplemented
domains. The [React build-tool guidance](https://react.dev/learn/build-a-react-app-from-scratch)
and [Vite guide](https://vite.dev/guide/) describe this build setup; package
versions and compatibility metadata were inspected in the public npm registry.
The [Node download index](https://nodejs.org/dist/index.json) supplied the
Node 24 LTS release and bundled npm version; the Linux x64 archive matched its
published SHA-256 manifest before extraction.

## Implications
PD-07 creates development/build commands now, adds the remaining validation
tooling at Step 7, and validates the full scaffold at Step 8. The bare bootstrap
does not register product routes, invent domain types, or call providers/APIs.
PD-11 supplies generated clients; PD-12 wires CI; PD-13 extends the common
command front door. Build-tool changes remain coordinated shared-file work.

## Approver
Not required for the routine build-tool selection within the approved stack.
Suraj verified PD-07 Step 1; product inventory and architecture review retain
their later human-verification gate.

## Supersedes
None. Extends PD-02's selected toolchain without replacing it.
