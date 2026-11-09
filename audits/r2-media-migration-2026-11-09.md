## CORS applied by owner — 2026-11-09

- Dashboard CORS policy saved and tested using HTTP request Origin headers for three site origins.
- Automated sample verification: 6 representative MP3, M3U8 and TS objects × 3 origins = 18 positive HTTP 206 byte-range checks with exact Access-Control-Allow-Origin, MIME and source bytes.
- Foreign-origin negative probe returned HTTP 403 (expected deny).
- Reusable CORS JSON file now matches the Dashboard's top-level JSON array format.
- Review-only independent listening room: /signature/r2-transport-review/ (not part of search sitemap). Production still uses GitHub audio.
- This does not confirm a real iPhone screen-lock session, 10-minute splice listening, sleep timer or network resilience. The final cutover is still gated.

---
## Verified migration results — 2026-11-09

- GitHub Actions pilot run 42580141154: SUCCESS. 1 MP3 + 1 playlist + 10 TS segments = 12 objects / 30,285,642 bytes; full R2 GET SHA-256 and public GET Range 206 PASS.
- GitHub Actions full run 42580411665: SUCCESS. 35 MP3 + 35 HLS 7-day playlists + 325 MPEG-TS segments = **395 objects**, **978,167,562 bytes**, each independently read back from R2 and SHA-256 verified.
- R2 full pass: 383 new uploads, 12 pilot objects reused without overwrite; all 395 objects verified.
- Public Range: sampled 8 URLs spanning 2 masters, 2 playlists and 4 TS segments returned byte-exact 206.
- HISTORICAL: before owner configured CORS, origin request did not receive Access-Control-Allow-Origin. After owner saved policy on 2026-11-09, separate GitHub Actions cross-origin HTTP Range checks confirmed positive responses for all 3 site origins and MP3/HLS/TS samples. Actual iPhone native HLS lock-screen QA remains pending.
- All approved media copied without recoding; original GitHub Pages player, files, Sleep Timer, canonical and sitemap unchanged. No physical iPhone QA performed.
- The bucket token and GitHub credentials worked, but secret values were never printed.

---
# WhiteNoiseChoir — Cloudflare R2 staging and migration

Date: 2026-11-09. Status: upload and verification only. The live GitHub Pages player is unchanged.

## Identity and object layout
- Bucket: whitenoisechoir-media, Cloudflare account R2 endpoint from the bucket Settings, custom domain https://media.whitenoisechoir.com.
- Keep keys byte-path-compatible: audio/<id>.mp3; audio/continuous/<id>/continuous.m3u8; audio/continuous/<id>/part_NNN.ts.
- This avoids modifying 7-day HLS playlists, whose segment references are relative to each playlist.
- GitHub Actions repository secrets: R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY. Never commit or log secret values.
- Source of truth: catalog/library.json and audio/continuous/manifest.json (35 approved sources). Do not publish unrelated unapproved PR #21 sounds.

## Safety
- Runs from an isolated migration branch and does not modify the production website or delete GitHub files.
- Pilot phase uploads only the approved white-noise master, its playlist and referenced MPEG-TS segments.
- Full phase copies exactly 35 production masters, 35 playlists, and their referenced MPEG-TS segments. It does not copy unapproved candidate masters.
- No overwrite: if an existing object has incompatible size, SHA-256 metadata, or MIME type, the upload is blocked.
- Every uploaded object is downloaded through the authenticated R2 S3 API and checked against a locally computed SHA-256.
- Additional public custom-domain Range HTTP 206 tests compare binary bytes and Content-Type. Separate CORS and iPhone tests remain.
- No CORS configuration change is possible with bucket-scoped Object Read & Write S3 key. Owner must set bucket CORS in Dashboard.
- Do not switch main player base URL or delete old GitHub media until after full audit, CORS, playback tests, owner real-device listening and rollback acceptance.

## Owner: paste this policy through R2 bucket -> Settings -> CORS Policy -> Add CORS policy -> JSON
Configuration file config/r2-media-cors.json now uses the exact Dashboard JSON array format (copy entire JSON).
Allowed origins: https://whitenoisechoir.github.io, https://whitenoisechoir.com and https://www.whitenoisechoir.com.
Allowed methods GET and HEAD only; Range request header allowed; expose Accept-Ranges, Content-Length, Content-Range, Content-Type, ETag.
Cloudflare R2 docs: https://developers.cloudflare.com/r2/buckets/cors/

## Next-stage acceptance tests
1. Pilot R2 upload and full S3 GET SHA verification PASS.
2. Public custom-domain HTTP Range 206 checks PASS for MP3, HLS, first and final TS segment.
3. Set CORS and verify Origin allowed; rerun cache purge if previously cached assets lack CORS.
4. Full transfer (35 MP3, 35 HLS, all segments) with full-byte SHA verification.
5. Validate R2 independently in /signature/r2-transport-review/ (noindex) before adding a configurable media origin to the production player; preserve current GitHub fallback and canonical/sitemap.
6. Test Safari native HLS across 10-minute boundary, MP3 fallback, pause/stop, Sleep Timer, original 45 presets, mobile sizes and actual iPhone locked-screen playback.
7. Roll out player switchover only with a reversible feature flag and keep originals hosted in GitHub during a safe observation window.

## Price/traffic warning
Cloudflare R2 Standard charges operations after its monthly allowance; every HLS segment download may count as an object-read operation. Monitor class B requests and configure a budget alert. 7-day VOD playlists reuse a small fixed set of MPEG-TS objects; no 7-day per-track audio duplication is stored.
