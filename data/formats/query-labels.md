# Human-reviewed query labels, format version 1

**Origin:** PD-09 Step 5. The [empty draft template](../evaluation/query-labels.template.json)
is a format starter, not a labeled evaluation set. No final listing IDs, queries,
judgments, reviewer identity or review time have been invented.

Final population and review belong to
[SE-01 Step 9](../../docs/tasks/domain-task-list.md#se-01--implement-browse-search-filters-sorting-and-pagination)
after the real frozen dataset exists. The label set must be tied to that dataset,
the actual public search contract and the recorded human review. A preview
manifest cannot satisfy this dependency.

## Envelope

UTF-8 JSON with exactly the template's top-level keys:

| Field | Draft / reviewed meaning |
|---|---|
| `format_version` | String `1`, the label-file structure version. |
| `status` | `draft` or `reviewed`. This is recorded review state, not proof or authorization by itself. |
| `dataset.logical_data_fingerprint` | Null in draft; final logical dataset's SHA-256 fingerprint when reviewed. |
| `dataset.manifest_path` | Null in draft; repository-relative retained final manifest/evidence path. A consumer must validate the path safely; this is never an arbitrary file/URL instruction. |
| `dataset.schema_version` | Null in draft; the actual final schema version, not `preview-1`. |
| `dataset.source_revision` | Null in draft; exact accepted code revision that generated/validated the frozen final data. |
| `search_contract_revision` | Null in draft; exact reviewed contract revision defining query/filter/sort/eligibility inputs. |
| `review.reviewer` | Null in draft; actual named human who accepted the judgments. Never assign a name merely from a stream label. |
| `review.reviewed_at` | Null in draft; actual review time, six-digit UTC RFC 3339 ending `Z`. Do not infer timestamps. |
| `review.inclusion_policy` | Null in draft; explicit representative-query selection, context and inclusion/exclusion rules fixed before scoring. |
| `queries` | Empty template; later ordered query records below. Order is stable and query IDs unique. |

Each query record has exactly these fields:

| Field | Meaning |
|---|---|
| `query_id` | Canonical lowercase UUIDv4, assigned once and retained with the frozen label set. It is an opaque test identifier, never authorization. |
| `query_text` | Nonblank controlled query text meeting the actual search contract. No real contacts/private data. |
| `context` | JSON object containing only actual reviewed public filter/sort/eligibility inputs. Do not invent final domain field names. An empty object is valid only under an explicitly recorded reviewed default context. |
| `relevant_listing_ids` | Null means unreviewed and blocks scoring. A reviewed array contains distinct actual canonical listing UUIDs from the exact frozen dataset and eligible context. Empty array means the human judged no relevant listing, not missing labels. |
| `include_in_nfr04` | Null until the inclusion decision is reviewed; otherwise boolean according to the frozen inclusion policy. |
| `exclusion_reason` | Null when included; a nonblank human-reviewed reason when excluded. Never exclude a case merely because retrieval failed. |

No example query rows are supplied: placeholder IDs or generated judgments could
be mistaken for final evidence. The final SE-01 validator/evaluator must reject
unsupported/extra fields, malformed IDs/types/time, duplicate query/relevant IDs,
dataset/contract mismatch, missing referenced listings and unfinished review.
It must not infer review from a syntactically valid file.

## Human labeling and freeze procedure

1. **Verify prerequisites.** SE-01's owner verifies actual ID-READY/LI-CORE and
   domain schema/configuration, completed dataset population/integrity/index and
   availability checks, retained manifest/fingerprint, and real search contract.
   Identify the human label reviewer before labeling. Missing inputs block final
   labeling/DATA-READY/NFR-04; the draft template is not a substitute.
2. **Choose representative cases.** The owner and human agree selection and
   inclusion policy, contexts and at least 20 included representative queries.
   Include the intended range of search needs; do not select only easy known
   successes. Keep explicit exclusions and their reasons visible.
3. **Judge the frozen corpus.** The human checks relevance against actual eligible
   listing content/context from the fixed synthetic corpus, using a documented
   inspection method independent of the measured top-five result. Populate IDs
   from that corpus only. AI suggestions are review assistance, not human labels.
4. **Resolve and validate.** Resolve ambiguous judgments with the human; verify
   all references/contexts and at least 20 included reviewed cases. Record actual
   reviewer/time/policy and mark reviewed only after human acceptance. Commit
   through normal explicit commit/review gates; record the exact label revision.
5. **Freeze before scoring.** Tie the evaluator to exact code/data/contract/label
   revisions. Never regenerate labels or drop failed queries to improve a score.
   Changes after freeze need explicit review/versioned evidence and revalidation.
6. **Evaluate later in SE-01.** Success@5 is the proportion of included queries
   whose first five actual results contain at least one human-labeled relevant
   listing; the target is >=80%. An included case with an empty relevant set has
   no possible hit and remains unsuccessful. Exclusions require the preapproved
   policy; do not silently change the denominator. Preserve query-level outcomes
   and dataset/code/label fingerprints. Runtime failures or stale data are not
   hidden by missing samples; follow the approved evaluator/run manifest.

Keep the completed labels, final manifest/source inputs and evaluator evidence
in Git or the approved retained evidence location. The payload-only ignore rule
does not hide this template or final labels. Do not include secrets, private
payloads or real contacts in labels/evidence. The original PD-09 preparation supplies no evaluator or DATA-READY/NFR-04
result; the later isolated tooling checkpoint below retains those final gates.

## SE-01 isolated tooling checkpoint

[Evaluator preparation](../../scripts/evaluation/README.md) now validates this
format and exposes template validation and synthetic arithmetic checks only.
It cannot attest human review or perform final scoring. The actual final corpus,
human labels and real binding/retrieval integration remain pending; the template
is unchanged and no final label set has been created.
