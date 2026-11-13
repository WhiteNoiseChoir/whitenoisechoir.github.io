# Internet Archive music metadata adapter — Draft, 13 Nov 2026

## Relationship to current pipeline

- Builds **on top of Draft PR #83** (which itself depends on Draft PR #82).
- Existing Commons candidate index: 44 instrument/ambient families; 250 new metadata objects reported by successful CI run [43375067504](https://github.com/WhiteNoiseChoir/whitenoisechoir.github.io/actions/runs/43375067504) (plus 7 already present; not 257 downloaded audio files).
- This extension searches **Internet Archive** via its documented Advanced Search API, then obtains item metadata and original-file listings from its metadata endpoint.
- Both providers write candidate metadata to the existing private, content-addressed-by-source **`internal/music-candidates/v1/`** prefix. They share idempotent create-only `IfNoneMatch: *` writes; a candidate ID is NOT an audio SHA-256.
- Archive source revision metadata (SHA-1 when supplied) is an **unverified publisher field**, NOT a verified media digest.

## Copyright and validation gates

A source is eligible for **candidate indexing only** if it exposes an explicit CC0, CC-BY 3.0 or CC-BY 4.0 license URL on the search result AND the live item metadata agrees. CC-BY-SA, CC-BY-NC, malformed/missing claims and any mismatched claim are excluded. Original audio files only; derivatives and non-audio files are excluded.

Internet Archive licenses are **self-asserted**. Evidence flags remain `internet_archive_uploader_metadata_unverified`, `source_license_verified_at=null`, `source_claim_and_composition_rights_pending`. They require independent checks of author, composition, performance, identity, commercial-use rights and potential Content ID claims before download/publication. Do not treat the index as a copyright-clearance service. Music analysis fields (BPM, key, chords, musical role, mood, loopability, duration) remain null.

No API credential/token is needed for this provider, and **no audio bytes are downloaded**. The scanner does not touch Studio, mixer, site publication, audio sidecars, or the production catalog.

## Operational boundaries

- `scripts/scan_archive_music_metadata.py` — adapter; `--persist` opt-in.
- `scripts/test_archive_music_metadata.py` — offline fixture-based regression suite.
- `.github/workflows/music_archive_candidate_metadata.yml` — two independent shards, up to 500 candidates each per run; max 30 per family, 10 Archive item details per family, bounded search pages and retry/backoff.
- `--persist` writes private JSON to R2 under `internal/music-candidates/v1/`, plus run manifest `internal/music-candidates/runs/archive-<run>-<shard>.json`.
- Existing objects never overwritten; no downloads, transcoding, audio uploads or Studio releases.
- Workflow is scoped **only** to this feature branch; it must not merge/deploy automatically.

## Measurement and next gates

Compare two `ARCHIVE_METADATA_FINAL` log lines (shards 0 and 1) for `candidate_unique`, `persisted_new`, `persisted_existing`, `write_errors`, `downloads`, `audio_uploaded`. Read per-family `ARCHIVE_METADATA_GROUP` diagnostics: `items_examined`, `skip_no_eligible_license_claim`, `skip_no_original_audio`, `search_errors`, `detail_errors`. GitHub Actions success alone does not establish 1,000 candidates or independent object integrity.

If Archive responses are blocked/rate-limited or license claims are insufficient, record and report that limitation, **do not fake counts or loosen verification**. Future discovery sources should have explicit provider adapters with their own license evidence, provenance and authorization. Freesound API requires an access key and its API terms restrict unlicensed commercial usage; do not scrape or use it by default.

Separate R2 inventory audit, source-to-asset mapping, music feature extraction and Studio compatibility QA remain required. Keep PRs in Draft pending independent review.
