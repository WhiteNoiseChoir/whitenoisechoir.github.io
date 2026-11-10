# Wildlife Taxonomy Expansion — 2026-11-10

## Deliverable
**85 conceptual wildlife audio archetypes**, in **6 subgroups**, researched against Macaulay Library, BirdNET+, Xeno-canto and TiengDong. This is a curated category coverage seed, **not** a full scrape of all species nor evidence of 85 usable MP3 files.

## Breakdown
- Birds & Birdsong: **22**
- Insects & Other Arthropods: **15**
- Frogs & Amphibians: **8**
- Terrestrial Mammals & Pets: **21**
- Marine & Aquatic Wildlife: **11**
- Reptiles & Other Wildlife: **8**

## Use-case triage
- **SLEEP_CANDIDATE:** 16 (should still be listened to and QA tested).
- **RELAX_OR_EXPLORATION:** 59.
- **SFX_ONLY:** 10, not included by default in sleep collections.

## Important coverage principles
1. Treat **recording**, **vocalization type**, **habitat**, **species**, and **composite ambience** as different dimensions. Dawn Chorus is an ecological soundscape, not a taxonomic species.
2. Store actual species scientific names and taxon IDs only after individual verification. Both are null throughout this seed.
3. A single vocalization may last seconds and be unsuitable for ten-minute seamless loop. Do not label short repeated effects as 10-minute independent audio.
4. Macaulay Library recordings generally require explicit rights clearance for external and commercial reuse. Xeno-canto rights vary by recording; TiengDong is not a default rights grant.
5. Include ultrasonic bat sounds only when properly captured/transposed; disclose conversion accurately.
6. The `WILD-xxx` identifiers are research IDs; not production source IDs, playback destinations, indexable pages or media licensing evidence.
7. Avoid disturbing/abrupt animal sounds as default sleep sounds, especially for infants.

## Next actions
- Link each archetype to 1–3 candidate recordings with verified species/call/habitat and rights.
- Crosswalk with `catalog/master-catalog-crosswalk-2026-11-10.json` after merging the stacked taxonomy branches; auto dedup only after human confirmation.
- Prioritize environmental beds (dawn birds, crickets, night frogs) and soft isolated sounds (cat purr).
- Add a controlled-gap export by animal group, habitat, call type and license status.
- Keep production R2/HLS/MP3, canonical URLs and 45 preset recipes untouched.
