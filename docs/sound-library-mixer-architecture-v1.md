# WhiteNoiseChoir — Sound Library & Timeline Mixer, foundation v1
Decision date: 2026-11-10

## Product direction: asset-first, not 10-minute-master-first

**WhiteNoiseChoir is a reusable SOUND LIBRARY plus a timeline SOUND MIXER, with a later sound/video EXPORT STUDIO.** The sound library contains short effects, medium field recordings and long beds. Ten minutes is a *rendering target for a specific long-form product*, not an ingestion threshold. A two-second howl, an eight-second bird call, a train pass-by and a thirty-minute river can all be separately reusable assets.

### Existing production is frozen and preserved

- 532 concept/editorial entries, only 35 currently playable production sound sources, plus 45 established presets. These are NOT 532 downloaded files.
- Retain all existing HLS, MP3, mobile sleep/background behavior, canonical URLs and the indexed sitemap. No changes to the legacy player, SEO pages or production catalog in this foundation PR.
- The former C6 P0 queue is a **continuous-bed production queue**, not the master schema for every ingestible source. Its historic 605-second evidence gate must not spread to shorter effects. Keep historic C6 release checks for those candidates until deliberately migrated.
- Editorial concepts and physical files are many-to-many: one concept **wolves howling** might contain 30 different verified clips; one longer forest recording can be tagged with several concepts. Deduplicate using both file SHA-256 and perceptual/acoustic comparisons.

## Model: six independent data entities

1. **Concept/entity:** meaning, topics, SEO intents and translations, parent/child taxonomy, no implication of playable audio.
2. **Audio asset:** original or allowed derivative; uploader; source URL; saved rights evidence; license and attribution; bytes hash; measured length; codec; provenance; uploaded media storage; actual independent recording length; role and QA; raw distribution rights.
3. **Mix track:** a reference to an available, rights-cleared asset, with clip start, source trim, gain, pan, fade, optional loop and automation.
4. **Timeline composition:** tracks positioned at exact millisecond timestamps, duration, preset/scene and user modifications; versioned JSON can be saved and shared.
5. **Rendered product:** WAV/MP3 created on demand, MP4 later with user-selected royalty-cleared visual, video aspect ratio, image animation and display metadata.
6. **Web SEO content:** independent editorial review; group/hub pages by distinct search intent. 100 clips for wolves ≠ 100 automatically indexable pages.

## Example: river + wolf + birds + train

The machine-readable `catalog/mix-timeline-example-v1.json` illustrates a 15-minute scene:
- 00:00 flowing-stream bed continuously; adjustable base gain and smooth loop crossfade
- 02:00 a **single** wolf howl triggered; its volume and stereo pan editable
- 03:00 birds enter, then additional bird calls occur on a selectable schedule
- 05:00 train passes once, with left-to-right movement and volume envelope

Each layer controls gain independently, may be muted/soloed and can be placed, trimmed, repeated, delayed or moved. Later add random-but-seeded event scheduling to sound more organic; deterministic seeds ensure exported audio matches browser previews.

## Asset roles; no uniform duration or file requirement

- CONTINUOUS_BED: river, rain, fan, train interior, wind. Loops when appropriate; source may be shorter than playback; document truly unique source seconds.
- SEAMLESS_LOOP: high-quality self-contained loop, not an invented 10-minute independent recording.
- ONE_SHOT: wolf howl, bird call, twig snap, animal roar, bell.
- RECURRING_EVENT: bird chorus, cricket patterns, distant horn at scheduled intervals.
- PASS_BY: moving train, airplane, car; likely has a rise/fall envelope and pan automation.
- TRANSITION: thunder roll, door opening, seasonal/scene shift.
- TEXTURE: gravel, wind gusts, vegetation movement, room tone.
- SPEECH_OR_VOCAL: extra privacy, copyright and moderation controls; default excluded from ordinary sleep audio.

Short effects are particularly valuable because they are *timeline events*, not independent search landing pages or long HLS streams.

## Ingestion: maximize quantity of VERIFIED, USABLE files, not anonymous scraping

1. Research concepts against 532-item editorial registry; search many providers with a non-spamming query plan.
2. Retrieve **per-file** metadata, creator, direct legal source, published license, preview, and proof (including terms at acquisition time).
3. Resolve download rights, commercial use, modification, web playback, previewing, redistributing a source clip, YouTube export and third-party attribution. Do not assume royalty-free means raw distribution permitted.
4. Download permitted originals with an authorized account, provider API or direct media link. Temporary files are audited, originals stored in private Cloudflare R2, not in GitHub Pages. Public playback renditions are provided only after rights authorization.
5. Measure real duration, codec, sample rate, channels, peak, loudness, silence, corruption; compute SHA-256 and acoustic near-duplicate fingerprints.
6. Listen to excerpts and classify SFX vs ambience, voice/music contamination, random unwanted noises, artifact, dangerous volume spikes and the suitability of loops. A one-second source can pass as ONE_SHOT even if it fails as CONTINUOUS_BED.
7. Promote only rights-cleared and verified assets to **MIX_READY**, with separate public-preview and export rights flags. Master audio production and owner-approved public SEO release are separate actions.

### Source priority and constraints (checked 2026-11-10)

- **Freesound**: search CC0 first. CC-BY sound may be usable if full attribution is preserved; default exclude BY-NC for a commercial/YouTube project. Original download may require account login. Freesound API currently requires developer authentication, and commercial API applications have distinct licensing requirements. Source: https://freesound.org/help/faq/ and https://freesound.org/help/developers/
- **Wikimedia Commons**: freely licensed / public-domain media; verify each specific file's license and attribution. Source: https://wikimediafoundation.org/what-we-do/wikimedia-projects/commons/
- **Self-produced DSP / generated sounds**: WhiteNoiseChoir-owned sound design can cover fans, drones, synthetic atmospheres, rain-like noise, but do not misrepresent synthesis as true wildlife or field recordings.
- **Pixabay**: license prohibits standalone redistribution of content; do **not** ingest into a raw, downloadable public sound library by default. A composition-only alternative requires case-by-case terms review, not automatic approval. Source: https://pixabay.com/service/license-summary/
- **BBC Sound Effects**: no commercial use without licensing; exclude from ordinary commercial collection. Source: https://sound-effects.bbcrewind.co.uk/licensing
- **YouTube/ripped videos/music**: do not scrape arbitrary uploader recordings, music or videos without clear source/rights. Avoid bulk unauthorized downloads.

TinyFish is useful for discovering webpages and assisting login/navigation with the user's authorized session. It is **not** a bulk-binary-storage substitute or a waiver of download terms. Direct authorized media download/API and R2 storage are the proper pipeline.

## Suggested category coverage for collection

Nature/water; rainfall/thunder; wind/weather; forest/tree movement; wildlife—birds, wolves, wild mammals; insects/amphibians; ocean; domestic animals; rail/road/aircraft; boats and harbors; household/mechanical; urban/industry; fire/wood; domestic ambience; indoor room tone; footsteps and movement; doors/tools/objects; fantasy/science-fiction environments; transitions and timed accents.

Ingest **multiple distinct recordings per event type** with different ambience, location, distance, pitch, recording setup and clarity. Keep one semantic destination per user intent unless editorial analysis justifies splitting.

## UX roadmap

**P1—Library inventory**: search/filter by category, one-shot/bed, duration, origin, verified license, loop quality, preview, rights and upload status. Bulk authorized ingestion with batch QA, duplicate detection and R2 objects.

**P2—Mixer MVP**: 4-layer timeline, start positions with milliseconds, per-layer volume, mute, solo, loop, fade-in/out, independently scheduled one-shots and timeline seek. Web Audio API can handle interactive playback on supported clients. Preserve functioning legacy site; launch as an isolated `/studio-preview/` noindex route.

**P3—Composition saves & exports**: a versioned mix JSON shared with friends, client preview + server/headless FFmpeg authoritative render, WAV/MP3 output, then MP4 with a legal background visual. For long renders use a worker or bounded queue; do not force an all-at-once browser memory render on mobile.

**P4—Community/YouTube publishing**: user-created authored soundscapes, license/attribution manifest, differentiated thumbnails/visuals, meaningful unique mixes and titles, public template gallery after editorial review.

YouTube's monetization policy separately penalizes mass-produced or essentially reused content *even when usage permission exists*: https://support.google.com/youtube/answer/1311392. A CC0 recording and a technically legal export do **not** guarantee Content ID clearance or monetization. A creative, non-template composition and documented workflow are preferable.

## Immediate development constraints

This foundation PR adds a registry contract and an **unplayable demonstration timeline only**. It is not a new public route, approval, download or a completed mixer. All assets remain staged only when verified. Current 35 production sounds/45 presets untouched. The new source duration policy does not silently override existing strict regression checks for legacy approved ten-minute masters; those checks should be refactored deliberately by asset role in a follow-up.
