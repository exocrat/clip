# Hybrid development cases

`hybrid-search-v1.json` is SE-01 calibration input: eight controlled synthetic
listings and eleven queries, with ten intended positive queries and one intended
empty result. `relevant_keys` records **fixture-author intent**, awaiting human
review of this development report. It is not the final reviewed query-label file,
reference dataset, a generated human judgment or an NFR acceptance artifact.

The cases cover transport, books, furniture, phones, refrigeration, a telescope
at the end of a long description, a bicycle poster and an unrelated plant. They
include curated concepts, unfamiliar wording, a multiword alias, a misleading
keyword overlap/negation, long-source matching and an absent guitar. Literal
`telescope` tests lexical ending coverage; `watch stars at night` tests semantic
retrieval of that same source. Failure stays in the results.

Keep these cases separate from `data/evaluation/query-labels.json`. Do not tune
final labels or populate that file from this fixture. The development loader
accepts only explicitly synthetic/unreviewed development metadata and binds the
exact text, intent, UUID namespace, model and vocabulary to each score matrix.
Changing text or intent changes the fingerprint; review/version it before use.

The predeclared comparison grid lives in
`scripts/evaluation/semantic/calibration.py`; actual measurements run only through
an opted-in new private PostgreSQL cluster with the existing local model. The
analysis CLI compares captured scores without SQL/model work. See
[commands](../../../docs/environment/commands.md) and the
[proposal and limitations](../../../docs/architecture/hybrid-search-calibration.md).
