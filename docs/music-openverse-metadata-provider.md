# WhiteNoiseChoir Openverse metadata adapter — Draft (13/11/2026)

## Third source: Openverse official search API

This adapter targets **metadata discovery**, not audio importing. It builds upon Draft PR #84 (Internet Archive) → Draft PR #83 (Wikimedia Commons candidate index) → Draft PR #82 (parallel music audio intake).

- API: https://api.openverse.org/v1/audio/
- Search request: `q=<instrument-or-texture>`, `license=cc0,by`, `mature=false`, 20 results/page, max two pages per search.
- All requests use the documented API (no scraping), with 2.8 seconds between requests per shard, two shards maximum, retries honoring 429 Retry-After when present. Anonymous access is intentionally conservative; respect more restrictive server responses and stop if API terms prohibit further access.
- Excludes Wikimedia Commons and Internet Archive results at provider/source URL level to reduce overlap with existing imports.
- Accepts explicitly indexed CC0 or CC-BY 2.0, 2.5, 3.0, 4.0 source license claims; rejects NC/ND/SA and missing or inconsistent license evidence.
- Candidate stable ID is derived from canonical HTTPS source landing page. It is **not** an audio SHA-256.
- Provider-reported duration/bitrate/sampling-rate are stored separately as *unverified metadata*. Canonical technical and BPM/key/chords/loop/mood fields stay null until audio inspection.
- Source uploader claims (even CC0) are **not** independent rights/composition/performer/Content-ID verification. `rights_review_status` always remains pending. No music candidate is declared ready for commercial YouTube release.
- No audio is downloaded, transcoded, previewed, or marked as imported. No Studio access rules, mixer code, published catalog, or production presets are touched.

## Private storage and run evidence

Records go to `internal/music-candidates/v1/` via existing create-only `IfNoneMatch: *` helper. Reports go to `internal/music-candidates/runs/openverse-<runid>-<shard>.json`. GitHub Actions stores each shard's report artifact for 30 days.

Review both `OPENVERSE_METADATA_FINAL` log lines: `candidate_unique`, `persisted_new`, `persisted_existing`, `write_errors`, `downloads=0`, `audio_uploaded=0`. Check per-group API errors and validation exclusions. Sum candidate counts carefully: immutable source IDs prevent repeated records, but cross-provider overlap must still be audited.

Initial target is a **cap** of up to 500 candidates per shard, not a promise of 1,000 validated results. If anonymous API limits prevent full coverage, do not evade API limits, scrape, or use unapproved multiple credentials. Instead request Openverse-approved higher API limits or adjust the scan budget.

## Validation

`python scripts/test_openverse_music_metadata.py -v`

Follow with existing Archive, Commons metadata and music intake regressions in the dedicated workflow. PR remains Draft; does not merge/deploy.
