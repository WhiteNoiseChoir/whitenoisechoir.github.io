# WhiteNoiseChoir — private Music Candidate Metadata Index V1

## Purpose
Collect source metadata first, across 44 instrument/performance/texture hints. Candidate records are NOT audio files, instrument stems, rights-cleared songs, or mix-ready assets.

The current source adapter is Wikimedia Commons. It uses the existing commons.decide(..., allow_cc_by=True) gate (CC0 or CC-BY 3.0/4.0 with required attribution); a source license statement does NOT independently clear underlying composition/performance rights. Candidate records must therefore remain composition_and_reuse_rights_pending until a subsequent review. Never treat a candidate as mix_ready.

## Two parallel processes
- Nature/ambience: original independent nature harvester, unmodified.
- Music metadata: scripts/scan_music_candidate_metadata.py, sharded into 2 concurrent jobs. Uses public API category/search metadata, deduplicates by canonical source page + revision. No media downloaded or encoded during metadata discovery.
- Existing verified music audio pilot: independent pipeline in PR #82; not automatically triggered by this branch.

## Durable, private object structure
- Candidate JSON: internal/music-candidates/v1/<sha256-prefix>/<sha256-of-source-reference>.json
- Run provenance and IDs: internal/music-candidates/runs/<github-run-id>-<shard>.json
- GitHub Actions artifacts: music-candidates-shard-<shard>, 30-day retention.
- Object writes use IfNoneMatch: * to preserve previous records and guarantee idempotency. No existing media or sidecar is overwritten.
- Candidate ID is NOT an audio content hash. Audio ID, content SHA256 and storage key remain null until verified source bytes are downloaded.
- Provenance carries source page, revision, creator, license URL/evidence, claim verification time, original title/file bytes/mime, discovery hint/taxonomy, and review status.
- Music features (BPM, key, chords, loopable, mood) stay null without audio-based measurement. Instrument hints are explicitly unverified.
- candidate_only_not_downloaded status is intentionally conservative, even if same source has separately been uploaded. Reconciliation requires later source-to-asset crosswalk rather than filename guesses.

## Controls and boundaries
- Workflow path: .github/workflows/music_candidate_metadata.yml
- Default test+scan: 2 shards, capped at 500 unique candidates per shard, 38/group, at most 9 API requests/group, 4 parallel conditional R2 writes/shard. The target of 1,000 is a ceiling, not a promised outcome.
- Only internal/music-candidates/ receives writes. No Studio catalog, production audio, mixer, or deploy modifications.
- Never claim an increase in downloadable/mix-ready audio merely from candidate-index growth.
- Future providers require separate adapters, explicit license evidence, provenance verification and dedupe against existing source-reference IDs.
- Workflow can be manually re-run via workflow_dispatch; existing records remain unchanged.
- To review: compare actual MUSIC_METADATA_FINAL logs/artifacts for both shards, sum persisted_new and persisted_existing, and check per-group breadth. Overlap across shards may mean fewer unique candidates than the sum of discovered.

## QA
Run: python scripts/test_music_candidate_metadata.py -v
Also run existing 11 tests from scripts/test_music_instrument_intake.py.

This is a feature branch and draft PR. Review and validate before merging to main; no automatic Studio publication.
