# WS1 — Independent metadata diversity audit (DRAFT)

## Scope
Read-only scan of all private `internal/music-candidates/v1/<2hex>/<64hex>.json` from R2, not public repo.
Baseline 2026-11-13: 1,344 persisted metadata candidate JSON objects, verified schema+ID, **not** downloaded audio.

## Required deliverables
1. Script `scripts/audit_music_metadata_diversity.py` with offline tests and feature-only GitHub Actions workflow.
2. Group counts by provider, normalized instrument family, number of valid groups, license claim, review status, missing values, and source record age; count records with multiple classification hints.
3. Exact candidate-ID dedupe and separate normalized source media URL/page probable-overlap signals; NOT content SHA (audio not downloaded).
4. Coverage gaps (0/sparse families), provider dominance, repeated low-information records, and next 10 highest-impact family gaps.
5. JSON audit artifact + readable GitHub Actions summary. Redact any sensitive source URLs in public logs. Store full report only privately in R2 or restricted workflow artifacts.
6. All writes isolated to `internal/music-candidates/audits/` if needed. Preserve candidate objects untouched.

## Guardrails
Never add, change or delete existing candidate JSON, existing audio objects, production catalog, mixer, Studio, website, main branch or deployments. No auto merge. No API/audio downloads necessary. Audit data does not establish media/composition copyright clearance.
