# WhiteNoiseChoir — 13-Family Sound Library Foundation
Date: 2026-11-08
Branch: `feature/sound-library-foundation-20261108`
Source: user-provided `WhiteNoiseChoir_Full_Sound_Library_Blueprint_2026-11-08(1).xlsx`.

## Objective
Introduce a durable, source-driven library skeleton before producing additional audio. Preserve 22 existing production sound IDs, their 22 canonical Sound Pages, 45 live homepage mixes, the seven intent collections, the player and both HLS/MP3 playback paths.

## Current versus planned
- **22 current sound IDs**. Exactly 21 are owner-approved/arranged; Green Noise remains a separate pending listening review and noindex Sound Page. Being present in the current catalog must not be misrepresented as complete listening approval.
- **70 planned source concepts** (24 P0, 27 P1, 19 P2). `NEW-01`–`NEW-70` are planning IDs, have no media or licenses and must not be bound to Play controls. A future unique production ID requires original audio, license/source, measured duration, checksum, acoustic QA and explicit listening approval. Synthetic and CC0 status must always be disclosed accurately.
- **13 sound families**, mapped onto **12 existing physical category hub URLs plus one virtual Ocean family section** at `/sounds/#ocean-waves`. The current `/sounds/ocean-waves/` remains a **dedicated Sound Page**, not a group URL.
- **34 proposed mixes** (18 P0, 12 P1, 4 P2), retained outside the existing 45 preset engine. There are two source-set collisions: MIX-05 with `Sleep Fan with Rain` (same IDs, reversed gain-layer order), and MIX-09 with `Ocean and Wind` (same IDs and order). These should be reviewed, not published as unique new mixes. MIX-31 and MIX-34 require special three-layer level/peak QA before any future release.

## Source of truth
| File | Role |
|---|---|
| `catalog/library.json` | Existing 22 production IDs and 12 old hub references, unchanged |
| `audio/*-manifest.json`, `audio/continuous/manifest.json` | Existing audio provenance, master durations and HLS bindings, unchanged |
| `catalog/family-registry.json` | Family definitions, route roles, grouping, planned ID references |
| `catalog/planned-sounds.json` | 70 nonplayable proposals and release-gate placeholders |
| `catalog/mix-proposals.json` | 34 nonplayable mix proposals, dependencies and collision annotations |
| `scripts/build_sound_library_foundation.cjs` | Render/check two current-source/family grids and one forthcoming-family section from registry |
| `scripts/test_library_foundation.cjs` | Registry, SEO policy, route collision, inactive proposals and exact count integrity |
| `scripts/test_library_foundation_browser.cjs` | 320/390px fit, 13 family cards, 22 real sources, search, Ocean anchor, existing playback and timer persistence |

## UX / SEO release constraints
1. `/sounds/` retains its canonical URL, indexable status, original sound search/filter and progressive static HTML; 13 family cards are now visible. A future-listening section discloses the P0 candidates under family-specific details, with other plans counted only. It offers **no playback** for planned records.
2. Existing category hubs remain at their current URLs; their unique content and canonical/robots directives remain unchanged. The Ocean family uses only an on-page anchor. **No new SEO URLs or automatic indexed variants** are created.
3. The sitemap remains **18 URLs**. The 22 Sound Pages stay **10 indexable / 12 noindex**; Green Noise remains noindex. No page receives an indexing change during Foundation.
4. The 45 live mix recipes remain unchanged. Proposed mixes are planning records, not 34 new player modes or public SEO pages.
5. A generator makes the library HTML deterministic; `node scripts/build_sound_library_foundation.cjs --write` regenerates from the registry. Without `--write`, it rejects drift. Keep the 13 physical/virtual distinction rather than creating duplicate routes.

## Future acceptance gate (not yet done)
Before promoting any `NEW-xx` source: assign independent production ID, verify copyright/CC0 and attribution, measure independent audio duration and SHA-256, create proper master and HLS/MP3, complete acoustic and owner listening QA, validate mobile playback beyond 10 minutes, and only then change the catalog status. Separately judge SEO content and observed GSC query demand before adding an indexable page. Do not let new data flow directly into the legacy player until reviewed.

## Planned next production work
Begin Rain & Thunder P0 with Light Rain, Rain on Tin Roof and Distant Thunder as three audibly differentiated candidates. Review their original media/loops/levels, then activate one-by-one in the real catalog and in family navigation. Keep Rain on Window and Heavy Rain source pages unchanged until evidence warrants a specific URL decision.
