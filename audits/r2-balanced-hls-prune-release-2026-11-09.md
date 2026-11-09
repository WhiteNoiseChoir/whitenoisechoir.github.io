# WhiteNoiseChoir — balanced GitHub Pages HLS pruning release
Date: 2026-11-09
Status: feature branch QA, **do not claim Live until main Pages deploy SUCCESS**.

## Owner acceptance
The owner separately confirmed main WhiteNoiseChoir iPhone playback after production player migrated to `media.whitenoisechoir.com`. This authorizes the previously discussed balanced reduction, not deleting 35 original MP3 backups.

## Locked source proof
- Historical `main` recovery base: `9e005bb40ff986b9f7961f12bbb68cf2b49cc9ab`.
- R2 full upload GitHub Actions run #42580411665: authenticated full SHA-256 readback of 395 objects, 978,167,562 bytes.
- The prune ledger `audits/r2-hls-immutable-source-inventory.json` freezes Git blob SHA-1 identities and byte sizes of **35 native HLS playlists and 325 MPEG-TS segments**; 360 files, 514,374,326 bytes.
- This release removes 27 HLS groups / **297 objects = 430,033,063 bytes** and preserves 8 GH HLS groups / **63 objects = 84,341,263 bytes**.
- **35 GitHub MP3s preserved** with SHA-256 assertions against approved production manifest; original 45 presets preserved.
- Every one of the 27 affected sound pages now references **R2 HTTPS HLS**; old GitHub HLS paths are never requested by production player.
- GitHub's `audio/continuous/manifest.json` remains a historical **source-provenance manifest** of all 35 approved HLS even when 27 R2 object paths no longer exist locally. Tests rehydrate the approved byte-identical files into disposable GitHub Action workspaces and prove original Git SHA.

## 8 independent native GitHub HLS fallbacks
`white-noise`, `pink-noise`, `brown-noise`, `rain-on-window-real`, `box-fan-real`, `heavy-rain-real`, `ocean-waves-real`, `waterfall-real`.

For the other 27, Safari primary playback continues through R2 native 7-day HLS. If R2 fails, the player attempts R2 MP3 then the original **GitHub MP3**; MP3 loops are not guaranteed to be perfectly continuous behind iPhone lock during a Cloudflare outage. This is an explicit compromise. The special query `?audio_origin=github` uses GH native HLS only on the retained eight, GitHub MP3 on the other 27.

## Permanent safety checks and rollback
- `scripts/test_r2_balanced_layout.cjs`: verifies 27 remote stream routes, 8 real local HLS backups, all 35 master SHA-256 and original sound-page/data-hls references.
- `scripts/rehydrate_r2_hls_ci.py`: downloads missing R2-only HLS media into **CI temporary storage**, verifies source byte count and exact immutable Git blob SHA-1. Not committed.
- `.github/workflows/r2_balanced_hls_prune_qa.yml`: re-runs original 35-stream HLS decode and historical audio QA plus Chromium 6-scenario failover and emergency rollback tests.
- Legacy main-branch `continuous_hls.yml` publisher explicitly disabled so it cannot silently re-add retired media to GitHub Pages.
- Rollback the cleanup PR / restore exact 297 Git blobs from baseline commit; do not touch verified R2 objects. During any restore, verify Pages deployment at the intended SHA.
- Observability: monitor R2 class-B GET ops and Cloudflare cache behavior, and verify real iPhone playback after release.

## Accounting
The tracked Git HEAD tree size is estimated at ~**564.6 MB** at the staged branch commit (before final minor test/docs edits), down from 994.5 MB. This is **not** a statement about Git history size or the exact GitHub Pages published artifact size. Historical blobs remain in git history until separately pruned, which is not part of this release.

No audio is transcoded, regenerated or published without prior owner approval. Future media should be uploaded directly to R2; don't publish 10–20 MB audio or segment data to GitHub Pages.
