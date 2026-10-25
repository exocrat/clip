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
