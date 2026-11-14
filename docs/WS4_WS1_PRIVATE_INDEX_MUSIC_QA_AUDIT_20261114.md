# WS4 + WS1 evidence audit — 2026-11-14 22:22 ICT

## INDEX / CONNECTOR (inherited WS1)
- Source: PRIVATE `WhiteNoiseChoir/wnc-metadata-index`, `index/manifest.json`, generated `2026-11-14T11:34:15.512640+00:00`.
- Manifest: schema v2, source WS1 SQLite FTS5, WS1 SHA256 `7f5379d40ea8f9b6a94da642e201a747beeca547398ea857fc740f1e935d0401`; 22,239 records (nature 19,680; music 2,559), unique 22,239. Availability is `R2_OBJECT_LISTED=19680`, `METADATA_ONLY=2559`. Object listed is **not** audio decode/playback verified.
- WS2 overlay 6,500 PARTIAL; WS5 overlay 48 analyzed, 25 flagged, PARTIAL. Do not conflate with WS3 candidates.
- Public bridge GitHub Action run [43590543723](https://github.com/WhiteNoiseChoir/whitenoisechoir.github.io/actions/runs/43590543723) `sync` successful; log: `PRIVATE_CANONICAL_INDEX_OK` records 22,239, WS2 6,500, WS5 48, private_sync_done=true, updated=true.
- Read-only private shard probes succeeded: `music/ambient-pads/part-001.jsonl`, `music/grand-piano/part-001.jsonl`, `nature/aves/part-001.jsonl`; fields include provenance, license, R2 key, rights, role, QA and acoustic_analysis. Sampled music entries were `METADATA_ONLY` with no R2 key and `composition_role=UNKNOWN`; sampled nature entries were `R2_OBJECT_LISTED` with R2 keys but `composition_role=UNKNOWN`. This proves private GitHub reads, **not** authenticated gateway, low-latency API or true semantic search.
- Bridge workflow `.github/workflows/r2_metadata_private_bridge.yml` schedules UTC `17 */4 * * *` and uses private-only guard. GitHub Action success confirms sync at its execution time, not R2 freshness after that moment.
- SHA256 is manifest-reported, not independently recomputed from R2 bytes in this audit. Need independent source hash check and shard count/checksum audit.
- No evidence of live D1 gateway performance or authenticated GPT connector latency.

## COMPOSITION QA (WS4)
- 30-case original benchmark file exists and static regression run [43551548141](https://github.com/WhiteNoiseChoir/whitenoisechoir.github.io/actions/runs/43551548141) passed 3 tests. This is not real top-N retrieval.
- This branch adds 12 *editorial* nature+music/retention scenarios in `qa/ws4/music_retention_overlay_12.json`, extending coverage to 42 total cases. They include heavy rain/piano/fireplace, no melody, forest/flute, ocean/pad, snowy cabin/cello, baby lullaby separately, low music gain, 10h loop, no peaks/vocals, forest no music, guitar/rain, lake/harp.
- Observed actual shard data implies **0 confirmed playable RIGHTS-VERIFIED music hits** in the two music shards sampled; this is NOT a full-index estimate. Across all 42 prompts, top-5 P@5 and playable-music prompt rate remain **UNMEASURED** because no 42-case private retrieval outputs or composition/master rights verification were produced.
- Evaluator `scripts/ws4_composition_qa.py` currently uses `audio_status`/`r2_status` in `verified/ready/qa_pass` and nonempty R2 key, but canonical shard sample exposes `availability`, `playback`, `rights`, `qa_status` instead. The evaluator also counts any known license as `known_license_pct`, which is NOT composition/master rights clearance. A separate adapter and explicit tri-state (PASS/FAIL/UNKNOWN) rights/playback logic are required before claiming playable rights-verified music.
- Existing 30-case scoring matches family + role as a taxonomy **proxy**, not human graded P@5; lacks exclusion checks, compound-family matching, provenance, acoustic verification, intent/overlay scoring. New 12 cases intentionally remain editorial fixtures, not scored retrieval.
- Next safe batch: implement private JSONL search adapter with class/family/role/availability/rights filters and explicit unknown statuses; run top-5 for all 42 cases; compute P@5, prompt coverage, duplicate rate, known rights-composition/master rate and missing combos. Human grade relevance and compare ranking A/B. Run no audio download or publishing.
- US taste claims require actual YouTube Analytics CTR, first 30s retention and AVD; playlist observations are only proxies.

## Safety
- No private metadata rows or credentials committed to public repo.
- No production, Studio, WS2, WS3, WS5 changes.
- No audio downloaded, no video rendered/published.
- WS4 NOT complete. Owner has not approved acceptance thresholds; do not stop automation.
