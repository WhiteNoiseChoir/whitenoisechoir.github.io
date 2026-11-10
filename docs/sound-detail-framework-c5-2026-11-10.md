# WhiteNoiseChoir — Sound Detail Framework C5
Date: 2026-11-10
Status: Framework ready for review; no additional audio or canonical page approved.

## Scope
C5 standardizes the **editorial record**, release gates and reusable **sound-detail page blueprint** without changing the player or producing an MP3.

- `catalog/sound-production-registry-c5.json` — evidence-conservative ledger of 532 records keyed by `SND-0001...`
- `catalog/sound-release-approvals.json` — explicit human approval ledger; **currently empty**
- `framework-preview/sound-detail/index.html` — view an individual record using `?sound=SND-0040`; robots `noindex,nofollow,noarchive`
- `scripts/sound_release_gate.cjs` — read-only CLI to block unapproved releases
- `scripts/test_sound_production_registry_c5.cjs` and `scripts/test_sound_detail_blueprint_browser_c5.cjs` — source and browser QA

## Baseline
- 35 production catalog records: 34 catalog-approved statuses and one pending owner listening review (Green Noise)
- 449 potential sources lacking production audio
- 16 short SFX concepts (not automatically 10-minute sleep assets)
- 18 technical facets (not independent recordings by default)
- 14 soundscape or mix concepts
- 13 historical promoted plan records with explicit license and technical QA evidence
- 0 newly approved MP3, 0 newly approved sound detail pages, 0 new indexable pages

## Page content template: semantic and practical contract
1. Canonical intent and title: one distinct search intent; no alias/variant cannibalization
2. Parent hub and breadcrumbs: use actual existing routes
3. Acoustic description: listen to and describe the real master; never invent recorded duration or species
4. Playback controls: reuse production player, continuous HLS/MP3 fallback and Sleep Timer; none before media approval
5. Source audit: original page, license and attribution, independent original duration vs master arrangement duration
6. Technical QA: checksum, full-file decode, speech safety, dynamic range, seam/loop, iPhone/background playback
7. Owner listening approval: separate from automated validation; document date/reference
8. Related content: distinct acoustic peers and associated category, with no duplicate URLs
9. SEO: page creation permission, canonical, indexability and sitemap addition only after explicit review

## Release gate
The CLI is **read-only** and does not generate audio, pages, redirects or sitemaps.

```bash
node scripts/sound_release_gate.cjs --audit
node scripts/sound_release_gate.cjs --id=SND-0040
node scripts/sound_release_gate.cjs --id=SND-0040 --require-ready
```

The last command returns a nonzero exit code while the candidate is blocked. Recording an approval object is not by itself permission to publish: individual registry gates remain closed until a subsequent reviewed production change. A complete approval requires rights/provenance, evidence of acoustic QA, the owner's documented listening signoff, and an approved unique SEO route. For now, no candidate is approved.

## SEO and production non-regression
- Preserve all 12 old hubs and 6 newly built, noindexed hubs (18 total).
- Keep 28 logical groups as the taxonomy and 532 editorial rows in the sound explorer.
- Preserve existing 35 sound-page routes and audio, 45 presets, native HLS, MP3 fallback, Sleep Timer and mobile playback.
- No new Sound Page from a planned record; new blueprint is noindex and absent from sitemap.
- The 13 promoted items in earlier `NEW-` plans already link to existing production IDs; do not double count as 13 additional masters.

## Next phase
C6 will prioritize a reviewed audio production backlog, verify exact source rights/audio and obtain owner listening approval in small batches (5–10). Only then may a separate PR promote a candidate into production audio and its unique Sound Page, subject to all gates.
