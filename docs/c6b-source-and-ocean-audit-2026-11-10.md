# C6B — Ocean canonical QA incident and original-audio acquisition
Date: 2026-11-10
Scope: **verify historical site migration**, preserve all 35 production assets and 45 presets, then inspect two original 10-minute P0 source candidates. Not a new audio release.

## A. Root cause established from immutable GitHub history

Independent GitHub Actions run `42753068559` failed at `scripts/test_water_ocean_wave1_production.cjs` because the check retained SHA-1 Git blob pins from before the domain migration, not because an MP3 source changed.

| Item | Historical Git state | Current main | Verified difference |
|---|---|---|---|
| Ocean canonical `sounds/ocean-waves/index.html` | `13f684200c1b276276018895c5a0af9896c40a7e` (tree at commit `4100e4085b3e6b4160a10b840b4c1c0b71dd9bb9`) | `1ffb0a6e4e8368f3c37418cbfe2bbca4f6312573` | 2026-11-10 commit `4d72ee391464d4bc149dfdacd6707f4cb6d9ec7c`: exactly `whitenoisechoir.github.io` → `whitenoisechoir.com` **plus** `media.` inserted before `whitenoisechoir.com` in audio `contentUrl` |
| Sitemap `sitemap.xml` | `a3aebac7cc125f357d858730f4480f415ea298ea` (commit `1dc9eadc8c721d2ea2de27c91e46deeb6a6e5836`) | `1fb26b9e9186b3f9dba89234cc60c7bc3bb2228d` | 2026-11-09 commit `d37468ebd4ca09bb90ef4056406f3313358312cd`: only 18 URL hostnames change; all 18 pathnames remain identical |
| Persistent playback router `assets/persistent-router.js` | `e7c039730a8869ab037736cabbce9eb7b6cef65d` | `e7c039730a8869ab037736cabbce9eb7b6cef65d` | Exact unchanged Git blob |

The entire one-line Ocean HTML, after substituting the retired hostname to the production hostname and substituting the single audio URL prefix `https://whitenoisechoir.com/audio/` to `https://media.whitenoisechoir.com/audio/`, matches byte-for-byte. **No HTML, audio master, canonical route or sitemap is modified by this C6B incident-fix PR.**

The regression test now pins the reviewed new Ocean Git blob, asserts its canonical and media URL, excludes old hostname, retains robots `noindex,follow` and unchanged persistent router blob; it also checks the exact allowlist of 18 sitemap URL paths and a reviewed sitemap blob. Do not replace checksum values again unless a separate audited change documents why the bytes should differ.

## B. Two C6B candidate source leads

### SND-0039 — Crickets at Night
- Proposed original: [Night Time Crickets in New Jersey Suburbs](https://freesound.org/people/hargissssound/sounds/536332/) by **hargissssound**
- Freesound page declares CC0, **WAV 48 kHz, 24-bit, stereo**, 10:14.115, 168.7 MB.
- Nature of sound: crickets dominant, suburban traffic and people audible by uploader report.
- Acquisition **BLOCKED**: original WAV requires an authorized Freesound login/download; the project currently has no original bytes or SHA256.
- Whole-file recording independence and event/speech/traffic, source rights, music intrusions, peak/loudness and duplicate comparison remain untested.

### SND-0040 — Morning Birds
- Proposed original: [Morning birds — forest birds, cranes, lake](https://freesound.org/people/ali.g/sounds/855323/) by **ali.g**
- Freesound page declares CC0, MP3 **48 kHz stereo, ~180 kbps**, 43:00.099, 55.3 MB.
- Source is already lossy: MUST NOT describe as a lossless recording. Uploader describes a deer bark midway, likely unsuitable for uninterrupted sleep; selection of a clean 10-minute interval requires listening review.
- Acquisition **BLOCKED** for the same login/download reason. Original file metadata are not file-level evidence.

### Alternative Morning Birds lead (NOT selected)
- [Dawnchorus-uk.ogg](https://commons.wikimedia.org/wiki/File:Dawnchorus-uk.ogg), author **Silas S. Brown**, uploader declares **public domain**, self-recorded 2 Apr 2008; original OGG Vorbis 50:02, around 52 kbps and 18.5 MB.
- Public download access and license provenance appear stronger, but **source bitrate is very low for our quality bar**. No original has been downloaded or analyzed for audible compression artifacts. Keep as research/QA fallback only, do not promote blindly.

## C. Source review workflow
When authorized original WAV/MP3 is accessible, place it outside the GitHub repo or under temporary, private CI working storage; **never** commit 169 MB audio into a Pages repository.

1. Run `node scripts/c6b_source_probe.cjs --id=SND-0039 --file=/path/to/actual.wav` (or SND-0040 with its file). The source triage prints SHA-256, codec/container, container duration and whole-file FFmpeg decode results without changing approval or production records.
2. Independently verify rights, original uploader, exact license for those bytes and duration of genuine, non-repeated source; file container duration alone cannot prove ten original minutes.
3. Run full subjective/event/acoustic analysis and existing-35 A/B dedup; classify intrusive traffic, deer barking, speech/music or looping.
4. Produce a reviewed 600-second master **only after** selecting a safe, audibly suitable independent interval. Preserve original source provenance/hash, lossiness disclosure, reviewed master hash and loudness stats. No mislabeling, no unsupported sleep/baby efficacy claims.
5. Stage in `/signature/c6-review-audio/` with metadata gates, then unlock the noindexed `/framework-preview/c6-listening/` player for that exact master.
6. Owner listening approval is separate from mechanical QA; **zero new MP3s, zero new release approvals, zero new SEO/indexable pages in this PR**.

## QA
- C6 release queue remains P0=10, sources acquired=0, license verified=0, review audio=0, indexable new pages=0.
- Retain Green Noise waiting for owner approval.
- Independent old workflow failure at Ocean/Sitemap old SHA must now be re-run on the changed test with full R2 HLS rehydration, audio and browser QA; don't claim PASS from reading source alone.
