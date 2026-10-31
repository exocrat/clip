# NEXT-06 Step5 human relevance review package

**State: Mohit accepted all22proposed relevance groups and the inclusion policy without corrections.** [Accepted judgments](accepted-judgments.json) preserve the exact IDs and context. Final source/contract/integration/freeze binding and scoring remain pending; canonical draft fields remain null until those gates pass.

## Proposed inclusion and context policy

Review all22cases below, covering all9categories, literal names, synonyms and broader needs. Keep every case included, including failed retrieval or a judged-empty relevant set. Exclude only an explicitly documented out-of-scope/invalid query with human approval; keep at least20included cases. Do not choose or change judgments from measured top-five results.

Context: an eligible regular synthetic user; currently available listings only; no category/condition/price filters; page1, public page size20 (score only the first5), relevance sort, Hybrid mode. Architecture comparisons must preserve these settings and the same labels. Availability is stable until2026-12-01T00:00Z. Relevance concerns item suitability; price, negotiability and condition do not constrain these query texts.

## Proposed judgments to inspect

These topic groups are machine suggestions, not labels. Accept, narrow, broaden or replace each group from the catalogue. Accepted groups would expand to all currently eligible IDs in the candidate file; individual-ID exceptions can be supplied. No human reviewer/time or inclusion decisions have been filled in.

| # | Query | Suggested relevant topics | Eligible candidate IDs |
|---|---|---|---|
| 1 | android smartphone | android-smartphone | 19 |
| 2 | mobile phone | android-smartphone, iphone, basic-mobile-phone, dual-sim-smartphone, refurbished-smartphone | 92 |
| 3 | student laptop | student-laptop | 21 |
| 4 | portable computer | student-laptop, office-laptop, compact-laptop, refurbished-laptop, gaming-laptop | 93 |
| 5 | desk monitor | desk-monitor | 19 |
| 6 | computer display | desk-monitor | 19 |
| 7 | study desk | study-desk | 20 |
| 8 | work table | study-desk | 20 |
| 9 | linear algebra textbook | linear-algebra-textbook | 17 |
| 10 | mathematics book | linear-algebra-textbook | 17 |
| 11 | campus bicycle | campus-bicycle, commuter-bicycle, mountain-bicycle, road-bicycle, folding-bicycle | 82 |
| 12 | two wheeled vehicle | campus-bicycle, commuter-bicycle, mountain-bicycle, road-bicycle, folding-bicycle | 82 |
| 13 | electric kettle | electric-kettle | 18 |
| 14 | water boiler | electric-kettle | 18 |
| 15 | badminton racket | badminton-racket | 16 |
| 16 | sports racket | badminton-racket | 16 |
| 17 | backpack | backpack | 22 |
| 18 | student carrying bag | backpack | 22 |
| 19 | student computer | student-laptop, office-laptop, compact-laptop, refurbished-laptop, gaming-laptop | 93 |
| 20 | folding cycle | folding-bicycle | 17 |
| 21 | kitchen appliance | electric-kettle, toaster, rice-cooker, kitchen-mixer | 73 |
| 22 | study furniture | study-desk, office-chair, bookshelf | 56 |

Ambiguities requiring human judgment: “student laptop” is proposed narrowly to the named student-laptop topic; broaden to other laptops if suitable. “campus bicycle” and “two wheeled vehicle” include all five bicycle types. “work table” currently excludes dining tables. “sports racket” includes badminton rackets (the corpus has no other racket topic). “kitchen appliance” excludes the table fan. “study furniture” includes desks/chairs/bookshelves and excludes beds/dining tables. These assumptions are explicit so they can be corrected before scoring.

## Inspection materials

- [Complete1000listing catalogue](listing-catalogue.csv): exact IDs, titles, descriptions, topic/category, conditions, prices and eligibility windows, including200hidden/future/expired rows that cannot be relevant in this context.
- [Candidate ID sets](candidate-proposals.json): exact proposed eligible IDs for each query, independent of rankings.
- [Approved-format draft](../../../../../data/evaluation/query-labels.draft.json):22stable query IDs; every relevance/inclusion/reviewer/time/final-binding field remains null.

## Human review and final gates

Mohit should inspect the catalogue and proposed groups, then give numbered corrections or confirm which groups and policy are accepted. No reply is interpreted as review. The actual response time is recorded only when a judgment is supplied. Review may occur by topic because repeated records share item/synonym meaning; the complete CSV retains per-record differences and every ID for exceptions.

The query-label format requires accepted ID-READY/LI-CORE, final schema/settings, accepted source/contract revisions, corpus verification and freeze before final labeling/scoring. The current run has real local SQL/photos/model checks but trusted caller/storage fixtures; actual Identity/S3/cloud and accepted final binding are pending. Therefore this package stays draft even if provisional topic judgments are supplied. Do not create query-labels.json or claim20human-reviewed final cases/DATA-READY yet. Preserve proposal/query IDs and later bind accepted judgments to the exact verified corpus.


## Human confirmation recorded

Mohit explicitly confirmed acceptance of all22groups and inclusion policy without corrections. This resolves the topic ambiguities as proposed. Confirmation was recorded at 2026-10-30T12:46:38.764302Z. The earlier inspection time is unknown and has not been inferred. No further relevance confirmation is needed for these unchanged inputs; material corpus/context changes require revalidation.
