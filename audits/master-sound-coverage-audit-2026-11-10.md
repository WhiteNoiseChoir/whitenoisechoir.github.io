# WhiteNoiseChoir — Master Sound Coverage Audit (Phase A)
Date: 2026-11-10

## Verified GitHub baseline
- 35 records in `catalog/library.json` (3 approved, 29 listening-approved, 2 arranged, 1 dsp-review). **35 catalog records are not 35 independently recorded ten-minute audio sources.**
- 13 currently registered sound families, 12 physical category routes plus virtual Ocean.
- 70 planned concepts in `catalog/planned-sounds.json`: 13 marked playable/promoted; 57 remain nonplayable.
- 45 established mix presets should remain unchanged.
- PR #31 adds 38 *research-only* proposals, not yet merged; count as external input, not production or existing main-tree records.

## Research taxonomy v1
- 28 logical family/facet categories tracked in `catalog/master-taxonomy-research-2026-11-10.json`.
- 18 sound-focused categories in the first design plus 10 exploratory categories (ASMR, industrial, rural, fantasy, spatial, rhythmic, cultural, human/spoken, seasonal, extreme environments).
- These are logical classification labels, **not 28 actual web category URLs**. Spatial and seasonal are cross-cutting dimensions; Soundscape is a composition layer.
- Do **not** sum 35+70+38 as distinct new audio: 13 of the 70 planned concepts are already promoted, and research items may overlap. Semantic dedup requires mapping identifiers.

## Audit notes and knowledge gaps
1. Library still lacks a verified species-level census; an exhaustive scrape/validation of TiengDong, Macaulay and Xeno-canto has NOT been completed.
2. The uploaded myNoise Ahrefs keyword data is directional. Demand volume cannot be treated as proof of a universally complete sound inventory.
3. A broad sound ontology (such as BSD10k) is a cross-check, not definitive proof no category is missing. Compare against Freesound tags, field ecology habitat inventories and SFX collections.
4. No external MP3 redistribution is authorized by taxonomy research.
5. Numeric goals like 400–600 MP3 and 500–800 types are planning scenarios, not mandatory publishing quotas.

## Next execution tasks
- Review PR #31; only after reconciliation merge the research proposals or reference their identifiers in a future consolidated register.
- Implement crosswalk mapping from each sound ID, NEW-xx and EXP-xxx to taxonomy and canonical semantic identity, report exact deduped counts.
- Build a machine-generated gap report per family and priority, with provenance and license review status.
- Expand wildlife in phases: birds, insects, amphibians, mammals, marine animals and habitats; use species taxonomy and call type; verify source pages individually.
- Stage first 5–10 *unrepresented* P0 sources only after licensing and acoustic differentiation checks.

## Non-regression
This phase changes only research files. No production media, source registry, playback code, sitemap, canonical, indexed URLs, Pages config or 45 presets are modified.
