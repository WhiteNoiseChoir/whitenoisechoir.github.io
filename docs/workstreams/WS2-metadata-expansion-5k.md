# WS2 — Expand private music candidate metadata to 5,000 (DRAFT)

## Scope
Extend 1,344 already-verified private R2 records with genuinely new source-reference candidates.
Target 5,000 verified candidate JSON records, not 5,000 audio files. Future ceiling 10,000 requires separate evidence/budget review.

## Required deliverables
1. New provider/family query waves informed by WS1 auditing; do not blindly rerun Openverse's first two pages or the exhausted 1,000 cap.
2. Preserve source schema `music_source_candidate_v1`, stable ID and create-only `IfNoneMatch:*` R2 object semantics.
3. Multiple instrument families and representation types (one-shots, loops, stems, improvisations, acoustic, traditional); all as *unverified hints*.
4. Per-provider request limits, backoff, rate-limits, checkpoints by batch, stop on 5,000 VALID private JSON or repetitive zero yield/error/budget.
5. Separate feature-branch workflow with dry-run tests, 2 max concurrent discovery shards if safe, no dependency on main. Separate logs for created vs existing vs rejected.
6. Validate source-URL/format, preserve license provenance; no bypass of captcha/rate limiting. Count real keys after upload.

## Guardrails
No audio downloads in WS2; no production catalog, no public assets, no merge/deployment. No falsely implied commercial reuse. Avoid collisions with WS3 and existing audio ingest workflows through distinct prefixes/checkpoints and explicit throttling.
