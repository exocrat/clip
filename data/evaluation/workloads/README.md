# Browse/search workload profiles — isolated preparation

local-search-pilot-v1.json is the verified bounded local profile:2rps,5s warm-up,
10s measured,max2active clients,3s timeout,30HTTP request cap. It mixes browse,
Keyword cycle and Hybrid wheeled vehicle over3controlled native sources. The
expected UUID is from the explicitly synthetic native preview seed, not a human
label or final data. Any wrong/empty/private/malformed result is a visible failure.

browse/keyword/hybrid-nfr-draft-v1.json are deliberately not executable:20rps
browse/10rps search,300s target duration, unresolved final dataset oracle. Other
settings are draft proposals only. They require actual upstream/auth/images/final
corpus/request distribution/resource/cost/telemetry/run-plan approval. Keyword
and Hybrid series are distinct, and local preparation accepts no NFR. See
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
