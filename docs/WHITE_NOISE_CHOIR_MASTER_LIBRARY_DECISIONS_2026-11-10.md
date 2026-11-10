# WHITE NOISE CHOIR — MASTER LIBRARY DECISIONS
**Date:** 2026-11-10
**Status:** OWNER-APPROVED STRATEGIC DIRECTION — planning targets, not audited inventory
**Website:** https://whitenoisechoir.com/
**Repo:** https://github.com/WhiteNoiseChoir/whitenoisechoir.github.io

## Core objective
Build the broadest practical, well-organized library of environmental, sleep, relaxation and exploratory sounds. **Finish catalog/taxonomy and the structural website framework before producing the next wave of MP3.** Coverage without creating duplicate sound names, SEO cannibalization or meaningless 10-minute repeated effects.

## Verified baseline at planning freeze
- 13 logical families in existing family-registry; 12 physical existing hub routes plus one virtual Ocean family.
- 35 production catalog entries, not 35 verified independent ten-minute field recordings.
- 45 working mixer presets, all preserved.
- 70 earlier blueprint records; 13 explicitly promoted to production, 57 remain unplayable in the blueprint.
- 38 external research proposals staged in research PR #31.
- 85 Wildlife sound archetypes staged in research PR #34.
- 14 Freesound and four nonduplicate Commons recording source-page candidates in research PRs #35 and #37; these are unapproved research assets, not additional production audio.
- Existing research PRs #31–#38 are not to be mistaken for published website work.
- No new production MP3 has been released from the discovery sequence.

## Expansion targets — provisional capacity design, not validated counts
- **28 logical categories/facets** in the research taxonomy (not necessarily 28 independent public category URLs).
- Target about **600 sound types** at catalog level *only after each type is explicitly enumerated and deduplicated*.
- Target about **500 source audio assets total** over time, **465 additional** compared with current 35 records IF that target proves warranted.
- Target **200 approved presets/soundscapes total**, **155 additional** beyond 45 live.
- Previous UX/SEO design scenario: around **18 primary indexable-category candidate hubs**, preserving 12 existing physical hubs and evaluating up to six new hubs; those new URLs are NOT approved yet.
- Sound detail page count remains **TBD** after intent and content assessment. Earlier 400–500 detail-page figure is a scenario, NOT a production commitment or an automatic indexation quota.
- 28 logical groups include ~11 primary families, 13 facets, 1 composer, 3 cross-cutting dimensions in the current research representation. Do not generate one public URL per facet.

## 28 logical topic groups
01 Noise Colors
02 Frequencies & Tones
03 Drones & Textures
04 Rain & Thunder
05 Freshwater
06 Ocean & Coastal
07 Wind & Weather
08 Birds & Birdsong
09 Insects & Amphibians
10 Mammals & Wildlife
11 Fans & Ventilation
12 Household Machines
13 Transportation
14 Urban & Indoor
15 Fire & Warmth
16 Gentle & Baby
17 Meditation & Tonal
18 Soundscapes & Mixes
19 ASMR & Tactile
20 Industrial & Factory
21 Rural & Farm
22 Fantasy & Sci-Fi
23 Spatial & 3D Audio
24 Rhythmic & Repetitive
25 Cultural & Sacred Spaces
26 Human & Spoken
27 Seasonal & Holiday
28 Extreme Environments

## Catalog model and controls
Separate **family/facet → sound type → licensed individual recording → composed soundscape**.
- Each entity must have stable ID, English/Vietnamese names, one primary group, optional facets, habitat/material/physical object/species/call type, sleep suitability, relevance/priority, status, sources, confidence and dedup target.
- Distinguish real sound from synthetic DSP and mixed/composed audio.
- A sound type is NOT an MP3; a recording can serve many mixes; short wildlife SFX should not automatically become ten-minute sleep assets.
- Research sources (Spotify, Amazon Music, myNoise, TiengDong, Macaulay, Xeno-canto, Freesound, Wikimedia, BSD10k etc.) are taxonomy and evidence sources only until per-file licensing checks.
- Preserve existing SEO URLs, canonical/sitemap until editorial intent/keyword mapping is complete; index only differentiated, valuable pages.
- Preserve player, iPhone background looping, HLS/MP3, Cloudflare R2, Sleep Timer and all 45 presets.
- No auto-generating hundreds of thin pages, downloading/reuploading unlicensed recordings, or claiming technical QA is owner listening approval.

## Agreed execution plan (in order)
### Stage 1 — MASTER CATALOG V1 (NEXT, highest priority)
1. Inventory all current 35 production sources, 70 blueprint records, 38 research candidates and 85 Wildlife concepts, and resolve duplicates by semantic identity (not merely identical names). Separate 143 crosswalk records and 85 wildlife concepts without double-counting.
2. Expand 28 logical groups into enumerated subgroups and named sound types using domain-specific reference inventories. Identify missing major categories; avoid the false assertion of exhaustive coverage.
3. Produce one authoritative master dataset with 1 row per sound type and related recordings, explicit status: live / planned / research / collision-review / out-of-scope.
4. Publish an audit with **actual, counted** number of distinct sound types per group, existing and missing, and priority. Do NOT pad it to 600.
5. Add a machine-readable validation script and gap report; get owner approval of final taxonomy and quantities.
**Acceptance:** full explicit list, stable IDs, dedup summary, per-category counts, documented ambiguous cases, zero production changes.

### Stage 2 — WEBSITE FRAMEWORK
1. Map master catalog to existing hub routes and proposed additional family/facet navigation, without silently creating new indexed URLs.
2. Build planned-state browse/search/filter experiences and species/habitat/call-type filters; preserve source IDs, audio controls and working mobile playback.
3. Make noindex,follow or non-URL placeholders for unproduced concepts; no inert Play links.
4. Test 320/390px mobile layout, keyboard accessibility, existing player, SEO nonregression, and 45 presets on staging.
**Acceptance:** all approved sound types discoverable structurally; no loss of existing production functionality.

### Stage 3 — AUDIO PRODUCTION, IN WAVES
1. Prioritize 5–10 independent recordings per wave from truly uncovered P0 types, not based solely on easy access.
2. Acquire rights-cleared recording, record creator/license/source/hash and actual independent unique duration.
3. QA sound identity, noise contamination, LUFS/true peak, seamless loop, mobile HLS/fallback and background playback.
4. Provide review page with seek bar; owner listening approval before promotion.
5. Publish only approved audio and update catalog/SEO selectively.
**Acceptance:** audited new unique production audio, no false 10-hour/10-minute recording claims.

### Stage 4 — MIXES AND SEO
- Build composed soundscapes from quality-certified base sources; avoid duplicating MP3 for every preset.
- Prioritize SEO URL and international locales based on verified query intent, content uniqueness and GSC, not a page-count quota.
- Review coverage and discover new sound families periodically.

## Existing research work and merge ordering
- PR #31: 38 research proposals (independent, unmerged).
- PR #32: taxonomy foundation (unmerged).
- PR #33: catalog crosswalk stacked on #32.
- PR #34: Wildlife taxonomy stacked on #33.
- PR #35: source discovery stacked on #34.
- PR #36: audio QA gate stacked on #35.
- PR #37: Commons source discovery stacked on #36.
- PR #38: source probe workflow stacked on #37.
**Important:** No research PR should be represented as production merely by being open or staged. Do not prioritize audio probe work ahead of catalog/framework.

## Next concrete deliverable
**MASTER SOUND CATALOG V1 — full, deduplicated enumeration of named sound types across 28 groups, plus a concise matrix: group, current production, planned sound types, recordings needed, proposed pages (indexable TBD), priority and explicit coverage gaps.** The catalog must be verified and signed off before further MP3 production.
