# Browse/search workload profiles — isolated preparation

local-search-pilot-v1.json is the verified bounded local profile:2rps,5s warm-up,
10s measured,max2active clients,3s timeout,30HTTP request cap. It mixes browse,
Keyword cycle and Hybrid wheeled vehicle over3controlled native sources. The
expected UUID is from the explicitly synthetic native preview seed, not a human
label or final data. Any wrong/empty/private/malformed result is a visible failure.

browse/keyword/hybrid-nfr-draft-v1.json are legacy drafts and deliberately not
executable. Their final dataset oracle is unresolved. Local NFR-01/02 workload
profiles use a separate complete shape and remain preview-only; they require
reviewed full expected browse responses and representative Hybrid query inputs.
NFR-02 does not score relevance; NFR-04 owns the Success@5 threshold. They do
not replace the separate reviewed real-run plan for target/auth/capacity/cost/
telemetry.

`chat-nfr-v1.json` records the NFR-05 two-client schedule: 60 seconds of warm-up,
60 messages over five measured minutes, five-second spacing and deadline, and a
10-read/s concurrent background workload. It is draft-only. The browser event
observer now requires an exact manifest approval and shared target/session
preflight; it preserves raw background output and never accepts an NFR.
Keyword and Hybrid series are distinct, and local preparation accepts no NFR. See
[runner semantics and commands](../../../scripts/evaluation/k6/README.md).

`ecs-lambda-comparison-schedule-v1.json` contains the approved A/B schedule,
not run-specific evidence. `ecs-lambda-run-manifest.template.json` is copied
into `docs/evaluation/experiment/<run-id>/` for each real run and filled with its
actual revisions, target/data fingerprints, workload, timing, telemetry, cost
and evidence references. Validate the template or a completed copy with
`comparison_manifest.py`; validation records completeness and privacy checks but
never authorizes a run.

`ecs-lambda-case-corpus-v1.json` is a dataset-bound draft, not an executable
profile. Seven browse/detail cases have expected responses derived from the
frozen archive. Three Hybrid requests bind to reviewed relevance-label sets, but
their ordered expected responses remain unset pending final DATA-READY search
references and independent review. `prepare_comparison_corpus.py` recreates the
draft from the retained archive and refuses to overwrite an existing output.

EXP-05 pilot profiles are per run and use the same reviewed ten-case read mix,
with a 60-second 10-read/s warm-up, five-second drain and 120-second 50-read/s
measured burst. `exp05_pilot_profile_builder.py` reuses an already reviewed
comparison profile; each candidate target plan independently binds its exact
Lambda/ECS weight and is hash-linked into the 15-run pilot plan.
