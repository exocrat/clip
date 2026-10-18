# Listings-owned search query boundary

**Date:** 2026-10-18
**Origin:** PD-08 Step 1.

## Question
How will Search query authoritative listing data without private-table access?

## Options considered
- A Listings-owned public query interface, keeping indexes with authoritative data.
- A Search-owned projection, requiring backfill and reliable update synchronization.

## Selected choice
Use a Listings-owned public query interface backed by PostgreSQL native indexed full-text search. Do not introduce a separate synchronized Search projection in the initial MVP schema. Listings owns the underlying listing indexes; Search consumes the reviewed public interface.

During Step 2, Mohit approved explicitly using `pg_catalog.english` for both title/description vector construction and query normalization, with a Listings-owned GIN index. This supersedes the schema's earlier unaccepted `simple` suggestion. It does not pin the PostgreSQL server version or promise measured relevance. Any later configuration change needs reviewed index/schema changes and affected evaluation revalidation.

## Rationale
This preserves authoritative availability and ownership without adding projection synchronization to the foundation.

## Implications
PD-08 Step 2 specifies the indexes for affected-owner review. DL-00 defines the query signature, authorization and failure behavior; LI-01/SE-01 implement and verify the real boundary. This decision grants no direct private-table access.

Technical basis: PostgreSQL's [full-text introduction](https://www.postgresql.org/docs/18/textsearch-intro.html) and [table/index guidance](https://www.postgresql.org/docs/18/textsearch-tables.html) describe word normalization and explicit configuration for matching indexes/queries. SE-01 still must establish relevance and NFR outcomes with final data and labels.

## Approver
Mohit (C), explicit approval in the execution session. Affected-owner schema review remains pending.

## Supersedes
None; resolves the initial boundary alternative in shared conventions §12.
