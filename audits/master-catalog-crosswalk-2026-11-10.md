# Master Catalog Crosswalk — 2026-11-10

## Verified baseline

- **35 production catalog entries**, including **3 Ocean & Coastal** records explicitly reclassified from legacy `water`.
- **70 blueprint records**, of which **13** carry explicit promoted production IDs.
- **38 external-research records** (from open PR #31).
- **143 source records overall — not 143 distinct sounds or 143 MP3.**
- The research framework is on PR #32; this PR #33 is stacked on it.

## Classification outcomes

- `catalog_record`: **35**
- `already_promoted`: **13**
- `not_produced`: **55**
- `overlap_review`: **22**
- `research_new_concept`: **16**
- `mix_not_new_mp3`: **2**

Some original blueprints are already produced; others overlap or require distinct independent recordings. Labels `overlap_review` indicate similarities **not proven duplicates**. No candidate is deleted automatically.

## Sound family audit

| Family | Existing catalog | Unproduced blueprint | New unmatched research | Needs overlap review |
|---|---:|---:|---:|---:|
| Noise Colors | 10 | 1 | 0 | 0 |
| Frequencies & Tones | 0 | 0 | 3 | 0 |
| Drones & Textures | 1 | 6 | 0 | 1 |
| Rain & Thunder | 10 | 5 | 1 | 5 |
| Freshwater | 5 | 7 | 2 | 1 |
| Ocean & Coastal | 3 | 0 | 0 | 0 |
| Wind & Weather | 1 | 5 | 3 | 0 |
| Birds & Birdsong | 0 | 2 | 0 | 2 |
| Insects & Amphibians | 0 | 3 | 2 | 0 |
| Mammals & Wildlife | 0 | 1 | 0 | 0 |
| Fans & Ventilation | 2 | 5 | 0 | 2 |
| Household Machines | 1 | 5 | 1 | 4 |
| Transportation | 1 | 5 | 0 | 3 |
| Urban & Indoor | 0 | 4 | 0 | 2 |
| Fire & Warmth | 1 | 3 | 0 | 0 |
| Gentle & Baby | 0 | 5 | 0 | 2 |
| Meditation & Tonal | 0 | 0 | 3 | 0 |
| Soundscapes & Mixes | 0 | 0 | 0 | 0 |
| ASMR & Tactile | 0 | 0 | 0 | 0 |
| Industrial & Factory | 0 | 0 | 0 | 0 |
| Rural & Farm | 0 | 0 | 0 | 0 |
| Fantasy & Sci-Fi | 0 | 0 | 0 | 0 |
| Spatial & 3D Audio | 0 | 0 | 0 | 0 |
| Rhythmic & Repetitive | 0 | 0 | 0 | 0 |
| Cultural & Sacred Spaces | 0 | 0 | 0 | 0 |
| Human & Spoken | 0 | 0 | 0 | 0 |
| Seasonal & Holiday | 0 | 0 | 0 | 0 |
| Extreme Environments | 0 | 0 | 1 | 0 |

## Checks and limitations

- All 143 entries map to 28 valid logical taxonomy identifiers.
- **Ocean & Coastal** now correctly separates 3 produced ocean sources and 2 promoted blueprints from freshwater; legacy production IDs, category routes and sound pages remain unchanged.
- Only the 13 explicit `production_id` links are treated as authoritative source-to-plan matches. Title and acoustic similarities are provisional and need reviewer judgment.
- The taxonomy list is a coverage scaffold, not an exhaustive scraped inventory of TiengDong, Freesound, Macaulay, Xeno-canto or BSD10k.
- The names `catalog_record`, `already_promoted`, and `research_new_concept` do not imply a separate unique MP3 each.
- Metadata is insufficient to measure independent recorded audio duration, verified licenses for every new candidate or source quality.
- No new MP3, indexable URLs, sitemap changes, media source changes, audio modifications, mixer changes or preset changes.

## Next tasks

1. Make a machine-readable availability/gap report prioritizing P0 by family, avoiding named overlaps.
2. Extend Wildlife by habitat, species and vocalization subtype, marking all unverified names and links clearly.
3. Verify individual recordings, licensing and original duration before sending any P0 candidate to audio QA and owner listening approval.
