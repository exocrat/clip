# Private single-snapshot hybrid listing read

**Origin:** SE-01 hybrid amendment Step5 private-read checkpoint. Mohit verified
35/65 title/best-description blend,0.35 semantic cutoff, keyword-first relevance
tiers, no pre-pagination semantic cap and controlled503 behavior. He accepts the
vague telescope/stargazing miss. Version `hybrid-blend-v1` freezes this selected
implementation reference; it does not accept final relevance/NFR or activate a
public API/UI. The subsequent verified API checkpoint registers mode/relevance
and dispatches here only with explicitly managed helper injection. Normal startup
still has no helper; lifecycle and UI work remain pending. The model/encoding and
final labels are unchanged.

## Internal interface and prerequisites

**Category amendment (2026-11-01; draft-provider scope confirmed by Mohit):**
Current retrieval policy `hybrid-blend-v2-category` extends original/expanded
lexical matching to title, description and the current category display label.
`category_text.py` supplies the combined vector inside the eligible-row snapshot.
The semantic model, source fingerprint, 35/65 blend, cutoff and coverage checks
are unchanged. Earlier v1 measurements do not accept v2. See the
[approved scope](../decisions/hybrid-listing-search.md#category-text-matching-amendment--2026-11-01).

All code remains Listings-owned in `hybrid_read.py`. This is persistence/query
implementation, not a second Search-owned projection or public route. Actual
caller eligibility must already have been checked by the owning service. No
Identity fake is introduced into the application; real auth remains pending.

| Private operation | Inputs and purpose |
|---|---|
| `bind_query(text,spec,vector)` | Validate current pinned model/384-finite-unit vector and bind the trimmed original query hash. Hash/vector are excluded from repr and never returned/logged. Trusted code must establish real helper provenance; a valid shape alone cannot do that. |
| `hybrid_statement(request,now,threshold,embedding,compiled,relevance=False)` | Validate the existing generated query, aware server instant, price threshold and exact query/model/vocabulary binding; build one parameterized result statement. Compiled expressions come only from the owned compiler. |
| `read_hybrid_page(connection,request,now,threshold,embedding,relevance=False)` | Normalize through real PostgreSQL, execute the result statement and return the existing `Page[ListingSummary]`; no model/pool/credential discovery. |
| `search_hybrid_page(connection,helper,request,now,threshold,relevance=False)` | On an explicitly supplied idle autocommit connection, encode the original query through the shared real helper and call the reader within20s. No inference under caller-held DB transactions. |

These private operations require nonblank text; missing text gives the existing
422 envelope. Ordinary browse/blank-query handling remains on the existing path.
`relevance=True` selects the new private relevance order; otherwise the existing
request's created_desc/price_asc/price_desc and their UUID ties retain meaning.
No generated enum/type/new public mode field is edited by this checkpoint.

The vector binding rejects a result for another query/model. Query hashing is an
internal consistency check, not authentication/model attestation. The helper
client separately validates actual pins/process/frames/coverage. Sources remain
owned by Listings; model vectors/private generation data never join responses.

## One result statement

The English/vocabulary/typo normalizer performs its existing read-only token
lookup first. Then **one SELECT** owns the following shared MVCC snapshot:

1. Input fixes the aware API-server UTC instant used for every availability
   predicate. Catalogue flags use the same snapshot as rows and coverage.
2. Eligible rows exclude retired/pending/unavailable/future/ended listings and
   apply category, condition, exact price and negotiability filters **before**
   coverage and scoring. Huge price bounds retain exact existing bigint semantics.
3. Require the one serving pipeline to match the query's exact supported hash and
   full encoding JSON. A different serving space is unavailable, never mixed.
4. Every eligible row must have a ready generation matching current source
   fingerprint, one title and all contiguous declared description chunks. Counts
   and ordinals are checked from chunks, not just the ready marker. Missing,
   pending, leased, failed, stale or incomplete eligible rows fail all coverage,
   even if they would not match the text or semantic cutoff. Ineligible gaps do
   not block. A valid pipeline with an empty eligible set returns an empty page;
   no supported serving pipeline still yields503.
5. Score complete current generations by exact native cosine:0.35×title plus
   0.65×maximum description chunk. Union original FTS, expanded/typo FTS and
   semantic score>=0.35; one row per listing. Retain keyword candidates below
   cutoff, with no hidden top-k semantic cap or per-page reranking.
6. Relevance orders original-term matches above expanded/typo matches above
   semantic-only matches, then descending blended score and ascending UUID.
   Recency/price sorts instead order that same matching set by their existing
   fields/ties. Row numbering precedes offset/size+1; fixed-corpus continuation
   is stable. Concurrent requests do not share a cross-page snapshot.
7. Only page-window rows become explicitly whitelisted summary JSON, including
   ordered active image references and exact integer money. No vectors, model
   IDs, source hashes, completeness flags, owner/selection/upload/object data or
   private creation time leave the SQL result mapper. Payload order is explicit.

Materialized CTEs make the intended eligibility/coverage/score boundaries visible;
correctness comes from the single statement snapshot and checks, not a claim that
CTEs make this scan fast. Exact arrays scan eligible parts; full-corpus plans/
CPU/memory/latency and production concurrency remain unmeasured.

## Controlled failure and limits

Missing capability/coverage, helper capacity/timeout/closed process, wrong vector
binding, invalid dependency data or native driver failure become existing
`ERRORS[503]`: **dependency_unavailable / Required dependency unavailable**.
There is no new public error code or keyword-only success disguised as hybrid.
Invalid active catalogue filters retain422 priority over coverage failure.

A503 is a normal HTTP error response. Test-only ASGI composition exercises the
existing error handler and verifies that a subsequent request still succeeds;
no website crash or global process shutdown is selected. Public retry/keyword
switch UI is still a later implementation/browser checkpoint. Keyword SQL remains
independent of registry/embedding readiness and of a closed helper.

High-level work deadline20s includes encoding/queue/SQL; the helper retains its
separately bounded cancellation/reap allowance. Reader statements use local3s
statement_timeout and1s lock_timeout within their transaction. External
cancellation propagates, rather than producing fake success. No heartbeat,
readiness cache, implicit bootstrap/model migration or background dispatch occurs.

## Tests and evidence

`test_hybrid_read.py` scripts driver receipts only: binding/configuration/input
bounds, SQL parameterization, projection/order, exact prices, readiness/422/503,
helper failures/no fallback, idle connection, cancellation and controlled HTTP.
`test_hybrid_read_postgres.py` separately runs actual PostgreSQL:

- Coordinate math validates blend/max-chunk/cutoff, keyword dominance, dedup,
  model-space rejection, partial/stale/failed/leased/pending/missing coverage,
  retired/ineligible gaps, filters/catalogues/huge integers, empty/late pages and
  stable69-row ordering at20/50/100 for all four orders. Coordinates are not
  inference/relevance evidence. The entire math fixture rolls back.
- A test-only advisory-lock CTE wraps the owned result statement. Server-observed
  waiting proves it started before another connection commits a source edit.
  That statement sees consistent old content/coverage; the next private read
  sees pending new source and503; fenced publication restores fresh reads. No
  production barrier flag or lock is added.
- The explicit actual-model opt-in publishes three controlled sources through
  the real worker/helper, reads typo/semantic queries through the new bridge,
  verifies missing coverage503 and filter-based recovery, closes the owned
  helper to verify503, and confirms keyword reads remain usable. One helper,
  <=30windows/10min/512MiB sampled host/helper; no new installs/downloads.

The shared test fixture helper now accepts an optional fixed creation instant
at INSERT time. The first native run attempted to rewrite immutable created_at;
that fixture mistake was fixed without weakening the existing origin guard.
Failed logs and successful runs were recorded in the historical receipt,
removed from the checkout; see the [evaluation retrieval guidance](../evaluation/README.md).
Current focused HTTP and native Hybrid read commands are in the
[command index](../environment/commands.md#se-01-hybrid-read-checks).

## Remaining gates

No app startup/public route/core/wire/generated/UI or deployment is activated.
Actual Identity/Listings acceptance, image/data boundaries, final corpus/20+
human labels, comparative evaluation, Linux/resources, full CI/secret scan,
independent affected-owner/exact-code review and all original FR/NFR/readiness
conditions remain. Public mode/relevance/503 UI must follow reviewed contract
registration/generation and human browser checks; cloud/hosting/push/merge keep
separate approvals. No SE-01/SE-CORE/DATA-READY completion is claimed here.
