# Master Catalog Crosswalk — 2026-11-10

## Scope
Verified from GitHub: **35 production catalog records**, **70 original planned records** and **38 research proposals from open PR #31**. These are **143 records**, not 143 unique audio files. Branch includes taxonomy foundation from PR #32; production `main` is untouched.

## Reconciliation outcome
- **catalog_record**: 35
- **already_promoted**: 13
- **not_produced**: 55
- **overlap_review**: 22
- **research_new_concept**: 16
- **mix_not_new_mp3**: 2

The 13 blueprint items with explicit production IDs are marked `already_promoted`. A source record with a similar title can be a distinct acoustically meaningful recording and is never automatically deleted or merged. All candidate collisions are manual review only.

## Per-family counts
| Family | Current catalog | Unproduced blueprint | New unmatched research | Overlap-review records |
|---|---:|---:|---:|---:|
| Noise Colors | 10 | 1 | 0 | 0 |
| Frequencies & Tones | 0 | 0 | 3 | 0 |
| Drones & Textures | 1 | 6 | 0 | 1 |
| Rain & Thunder | 10 | 5 | 1 | 5 |
| Freshwater | 8 | 7 | 2 | 1 |
| Ocean & Coastal | 0 | 0 | 0 | 0 |
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

## Gaps and next work
1. Link species-specific wildlife concepts to call type, habitat, Latin name where known; do not invent scientific names.
2. Audit actual 35 source *recording* lengths and provenance from manifests before forecasting independent MP3 hours.
3. Validate pairs with tentative overlaps via human review. `overlap_review` does not mean duplicate.
4. Add source/rights/licensing checklist for 38 research proposals before production.
5. Establish gap dashboard with priority, family, source availability, QA readiness and SEO intent. Do not create indexed pages automatically.

## Safety and non-regression
Only research JSON and report are added. No player, site routes, audio, sitemap, current source IDs or 45 presets changed.
