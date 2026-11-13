# WS3 — Controlled rights-checked music-audio import to R2 (DRAFT)

## Scope
Read private `music_source_candidate_v1` records discovered by Commons, Internet Archive and Openverse. Build an independent and **conservative** selector to move only eligible CC0 candidates into a small, validated pilot. Source license metadata alone is not sufficient; underlying composition/performance rights remain pending unless evidence can be independently established.

## Required deliverables
1. Reuse existing `harvest_music_instruments_to_r2.py`, `harvest_commons_cc0_to_r2.py` and `fast_sound_asset_intake.py` patterns where suitable.
2. Candidate states: DISCOVERED, RIGHTS_NEEDS_REVIEW, ELIGIBLE, DOWNLOADED, VALIDATED, STORED_R2, CATALOGED, STUDIO_READY, QA_LISTENING_PENDING. Never advance status without evidence.
3. Strict HTTPS/domain allowlist (including redirects), safe media extensions/MIME, file-size cap, ffprobe, SHA-256/dedup, R2 HEAD verify, attribution/evidence, object-level immutable storage. No unsafe URL fetch/SSRF.
4. Separate preflight/dry-run then a pilot batch up to 8 **source-verified CC0** files / 250 MiB cumulative, two download workers maximum, no surprising costs. If clearance cannot be established, **download zero** and report blocker, do not silently relax.
5. Log detected/selected/downloaded/validated/stored/cataloged/studio-ready independently; never count preview/source URL as stored asset.
6. Write to content-addressed private asset prefix and sidecar metadata; do not auto-add Studio manifest. Mark QA pending unless actual listening occurs.

## Guardrails
No unreviewed CC-BY or music with uncertain composition rights, no release/publication, no `main` merge, no changes to Studio, mixer, timeline or video preview. Do not write credentials to repo or logs. A cleanly skipped batch is valid if no rights-safe samples exist.
