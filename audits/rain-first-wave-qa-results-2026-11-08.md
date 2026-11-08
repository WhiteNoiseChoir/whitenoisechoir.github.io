# Rain & Thunder — First wave review results (2026-11-08)

## Release boundary
Exactly three **10-minute owner-listening review MP3 files** are committed on the feature branch. These are NOT in `catalog/library.json`, `audio/`, production HLS, the 45 preset recipes, or the sitemap. The noindex room under `/signature/rain-review/` allows A/B against existing Rain on Window and Heavy Rain. No player engine modifications.

The GitHub Actions builder run `42464712969` succeeded and committed three files in the branch. SHA-256 checks and real decoded audio inspection are enforced separately in `rain_review_qa.yml`.

## Measured review files
| ID | Independent source included | Output | ffmpeg mean dBFS | ffmpeg max dBFS | Owner state |
|---|---:|---:|---:|---:|---|
| `light-rain-review` | 605 s selected from 24m15s joedeshon CC0 preview | 600 s | -33.7 | -9.6 | PENDING |
| `rain-tin-roof-review` | 605 s selected from 56m30s archerjosiah CC0 preview | 600 s | **-48.9** | -8.0 | PENDING; LOW MEAN LEVEL |
| `distant-thunder-review` | about 145 s from 2m31s moxobna CC0 preview | 600 s, approximately 5 source cycles | -35.6 | -9.1 | PENDING; REPEATED THUNDER |

**Critical audio caveat:** Tin Roof has unusually quiet average output relative to transient maxima. Do not normalize solely based on average gain without a compression/true-peak assessment; high crest factor can lead to unexpected louder drops. Owner must compare at safe levels before any production release. The thunder source necessarily repeats recognizable acoustic events. Neither technical PASS nor 600s duration is human listening approval.

**Source bitrate metadata correction:** the long public Freesound HQ previews were downloaded as the first 20 MB only because their original recording lengths are over 20 minutes. FFprobe's `format.bit_rate` is then derived from a truncated file byte count divided by the *original header duration*. The earlier reported 47.19 kbps (Tin Roof) and 109.92 kbps (Light Rain) were invalid estimates, NOT measurements of their actual encoded stream bitrates. These fields are explicitly `null` in the reviewed manifest. The short Distant Thunder preview was not truncated.

The original source WAV files were **not** downloaded. These CC0 samples are preview-derived lossy MP3s; output 192 kbps MP3 is a delivery format, not restored original quality. Provenance/source links:
- Light Rain, joedeshon: https://freesound.org/people/joedeshon/sounds/430765/
- Tin Roof, archerjosiah: https://freesound.org/people/archerjosiah/sounds/843483/
- Distant Thunder, moxobna: https://freesound.org/people/moxobna/sounds/107518/

## Quality gate and limits
- Node QA: all source IDs, review flags, noindex, correct 22 source/70 planned/45 recipe isolation, no new sitemap URLs.
- Python real audio QA: actual filesystem MP3 bytes, SHA-256, ffprobe codec/stereo/rate/duration/bitrate, PCM samples decoded at multiple offsets, no numerical corruption, source/repetition provenance.
- Playwright QA: 320/390 px, real audio 600 s metadata, seek to last five seconds, one native loop flag, local review note persistence, no playback on page load.
- Listening QA: **pending owner**. Technical QA cannot establish perceived naturalness, playback comfort, individual device volume/SPL or locked-iPhone continuity. This review room uses a basic MP3 native loop, not a 7-day HLS stream.

## Next step (not authorized by technical tests alone)
Listen to each against original Freesound previews and existing WhiteNoiseChoir sources, resolve Tin Roof level and repeating thunder if needed, obtain higher-quality source originals, then make final owner-approved masters and 7-day HLS with explicit source IDs. Evaluate SEO intents separately; the 22 existing canonical Sound Pages and 18 sitemap entries are unchanged.
