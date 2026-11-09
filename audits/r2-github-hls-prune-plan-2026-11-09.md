# R2-first storage optimization — 2026-11-09

This is a **non-destructive planning & audit release**. Production media files remain untouched.

## Measured repository tree
- Main commit audited: `6703736c3ea9ae57d611628d2d2fd2ff99fdf7d8`.
- Git-tracked HEAD tree: **994,532,050 bytes** across 655 files (not the total Git history and not a measurement of the actual published Pages artifact).
- 35 production HLS playlists + 325 MPEG-TS segment blobs: **514,374,326 bytes** across exactly 360 paths.
- The R2 object-copy job `42580411665` separately verified 395 objects, 978,167,562 bytes (including 35 MP3 masters). HTTPS public CORS/Range QA passed. Dashboard custom domain is Active.
- 35 original approved MP3s remain at GitHub Pages; GH HLS is currently required by the fallback candidate chain in `index.html`.
- All 360 HLS blobs are pinned in `audits/r2-hls-immutable-source-inventory.json` with exact Git SHA-1 and size to support later audit and ref restoration.

## Three options with precise tradeoffs
| Scenario | HLS objects removed | Bytes reclaimed from tracked HEAD tree | Estimated tracked tree afterward | Consequence |
|---|---:|---:|---:|---|
| **Current: retain 35 GH HLS** | 0 | 0 | 994,532,050 | Full independent GH native HLS fallback; very little headroom |
| **Balanced: retain 8 high-intent GH HLS** | 297 (27 HLS playlists/segments) | **430,033,063** | **564,498,987** | Native GH HLS fallback for White/Pink/Brown, Rain on Window, Box Fan, Heavy Rain, Ocean Waves, Waterfall; other 27 fall back to local MP3 |
| **Maximum: retain 0 GH HLS** | 360 | **514,374,326** | **480,157,724** | Native GH HLS backup is lost for all sources; fallback becomes GitHub MP3 and may not loop reliably with an iPhone locked during R2 outage |

Recommended: **balanced** if post-production live iPhone acceptance and graceful fallback are explicitly confirmed. This keeps 8 of the highest-intent GH streams available for native iOS continuous playback and more than 430 MB tracked-tree capacity. The second option has not been implemented.

## Hard gates before any binary deletion
1. **Main player on iPhone, not only the R2 review room, must be listened to and approved after commit `6703736c...`:** start/stop, >10 minute boundary, lock-screen audio, 15-minute timer and multi-layer mix.
2. Select backup tier; do not remove GH HLS for a source without updating the source resolver to skip unavailable local HLS. For the chosen eight source IDs, preserve GitHub HLS fallback.
3. Verify R2 has all 35 MP3s/35 HLS/325 segments, strict hashes, Range=206, Content-Type and CORS. R2 price depends on requests, not just storage: configure billing budget alert.
4. Keep all 35 GitHub MP3 production backups and 45 presets unchanged. Never delete MP3s because historical review pages and original player depend on them.
5. Snapshot each retired blob identity before deletion (ledger now complete). Run tests in a **separate draft PR**, including R2 outage fallback, manual `?audio_origin=github`, 35 HLS integrity, 320/390 mobile, SEO/sitemap, and post-deploy smoke on real media.
6. Adapt all CI tests that read retired HLS paths to explicitly verify R2 instead of silently removing assertions or bypassing tests. Preserve or replace legacy HLS manifest/index contracts.
7. Merge only when CI + physical iPhone QA pass; verify exact SHA published. If playback degrades, revert the single cleanup PR (restoring GitHub HLS files) while R2 remains the default.
8. Observe live behavior before removing any remaining GitHub copies. Do not assume removal from HEAD shrinks total Git history or account storage instantly.

## Why storage pruning is worthwhile
GitHub Pages documents a 1GB published-site maximum and a recommended 1GB repository size, plus a soft bandwidth limit of 100GB/month. Since audio playback now uses the R2 custom domain, future audio must be uploaded directly to R2 without adding another 10-20 MB master to Pages.

Docs: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits

This document does not authorize deleting assets or re-encoding owner-approved audio.
