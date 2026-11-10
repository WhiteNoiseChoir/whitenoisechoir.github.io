# WhiteNoiseChoir — C6A: first ten independent MP3 candidates
Date: 2026-11-10 · Status: P0 queue and locked audition template only

## Baseline (unchanged)
C5 main `de7395aab4a9cf41c15dfff83776453cdcdc328e`: 532 inventory records, 35 existing production audio sources, 45 presets, 28 logical categories, 18 physical hub pages, C5 release approvals empty. Nothing in this PR creates an MP3, HLS segment, public detail URL, sitemap entry, indexable page, or new listening approval. Green Noise remains pending.

## Ten ranked P0 independent-audio candidates
| Rank | Registry ID | Candidate | Source plan | Intent |
|---:|---|---|---|---|
| 1 | SND-0039 | Crickets at Night | Field recording | Adult sleep, relaxation |
| 2 | SND-0040 | Morning Birds | Field recording | Relaxation, focus |
| 3 | SND-0037 | Campfire | Field recording | Relaxation, adult sleep |
| 4 | SND-0041 | Tower Fan | Field recording | Adult sleep, focus |
| 5 | SND-0043 | Hair Dryer | Field recording | Baby ambient listening, adult sleep |
| 6 | SND-0060 | Wind Through Trees | Field recording | Relaxation, focus |
| 7 | SND-0036 | Bamboo Water Fountain | Field recording | Relaxation, focus |
| 8 | EXP2-0144 | Night Sleeper Train | Field recording | Adult sleep, relaxation |
| 9 | SND-0046 | Womb-like Sound | Original synthetic DSP | Baby ambient listening |
| 10 | SND-0044 | Dishwasher | Field recording | Adult sleep, ambient listening |

The ranking is **editorial judgment**, not validated keyword volume, available CC0 source ranking, or production readiness. All ten currently lack a sourced original, verified per-file license, independent duration, produced master and audio QA evidence. No one may describe them as produced or ready to listen. SFX, technical-only variants and mix concepts are explicitly excluded. The XML sitemap is unchanged.

## Dedup / interpretation
- SND-0040 unifies NEW-17, EXP-014, WILD-001; SND-0039 unifies NEW-16 and WILD-023. Do not duplicate these aliases.
- Campfire must differ from existing indoor Fireplace.
- Tower Fan must differ from existing Box Fan/Desk Fan and AC; Hair Dryer and Dishwasher must not be renamed fan recordings.
- Wind Through Trees must be real foliage/wind, not relabeled synthetic Gentle Wind.
- Morning Birds must differ from existing Bodetal Brook & Birds.
- Bamboo Water Fountain retains the previous **source-blocked** caveat. Do not reuse an unverified Bamboo master.
- Womb-like Sound must be a fresh full-duration DSP render, not a renamed Low Rumble or Brown Noise. No infant/medical outcome claims.
- Night Sleeper Train is a continuing train-cabin bed, not a transient pass-by SFX or renamed airplane cabin.
- Full audio fingerprint, hash and listening A/B must confirm source/master novelty; semantic labels alone do not establish uniqueness.

## Source and license gates (next step; not complete)
For **each specific recording**, capture creator, exact source landing URL, original file SHA256, screenshot or stable license evidence URL, exact licensing terms/attribution, recording rights concerns, original file format, recording length and acquisition date. Prefer long original WAV/FLAC when available; Freesound's site license information must be verified on each sound's individual page. CC0 is not automatic and a lossy preview is not a lossless recording. Do not assume a creator has rights to third-party music/speech. Use no unlicensed source. For original DSP, retain source algorithm, seed(s), generation source and evidence of originality, not an invented CC0 claim.

For this C6 batch, require **at least 600 independently recorded/rendered seconds** before editing; any 600-second master assembled from shorter material is *not* an independent ten-minute original and is blocked as such. All masters still require controlled encoding and full-file checks (decoding, loudness and peaks, clipping, DC and silence, speech/unwanted transients, repeated snippets, loop seam, spectral novelty, MP3/HLS segment continuity, R2 and iPhone/Safari/background/sleep-timer). Technical PASS never implies subjective listening PASS.

## Review room
After rights and source-duration verification plus whole-file acoustic QA, a separately staged MP3 can be enabled in `/framework-preview/c6-listening/`. It has a native seekable player, explicit slider and “jump to last 5 seconds”. **Until then these controls intentionally remain locked**; there is no fake review sample or automatic approval. Review sources must be staged under `/signature/c6-review-audio/` and have pinned SHA256 fields and reviewed QA metadata. Owner listening signoff is documented separately via the release ledger and a PR.

SEO cannibalization, page URL, indexability, structured data and sitemap require a later specific editorial approval. Keep all C6 preview URLs noindex. No release gate in C5 has been relaxed.

## Known independent QA failure
The preexisting independent `Approved Review Audio Dedup — Independent QA` at workflow run [42750329700](https://github.com/WhiteNoiseChoir/whitenoisechoir.github.io/actions/runs/42750329700) failed in `scripts/test_water_ocean_wave1_production.cjs` while asserting the Ocean Waves canonical-page checksum. This C6 PR does not fix or suppress that error; investigate expected-vs-actual change provenance separately before any checksum correction. Existing Rain/Player/Batch18/R2 checks passed at the C5 main commit. A passing isolated C6 queue test does **not** cancel or override that independent failure.

## Files and verification
- `catalog/sound-production-queue-c6.json` — ten P0 records and conservative, closed evidence gates
- `framework-preview/c6-listening/index.html` — noindex, locked review UI with seek and near-end controls
- `scripts/test_sound_production_queue_c6.cjs` — structural, registry, no-premature-release, JS compilation, SEO baseline tests
- `.github/workflows/c6-p0-queue.yml` — PR and main CI for C6 and inherited C5 gate checks

Run `node scripts/test_sound_production_queue_c6.cjs` and `node scripts/test_sound_production_registry_c5.cjs`.
