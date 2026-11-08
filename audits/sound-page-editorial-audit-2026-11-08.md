# WhiteNoiseChoir — 22 Sound Page SEO/UX editorial audit

**Date:** 2026-11-08  
**Scope:** `/sounds/{slug}/`, 22 sound URLs; 22 source IDs; GitHub Pages production audio remains unchanged.  
**Reference:** `catalog/library.json`, `audio/cc0-sources.json`, `audio/continuous/manifest.json`, `scripts/test_field_sound_pages.cjs`.

## Baseline observed before this change

- 22 Sound Pages: **5 indexable, 17 noindex**.
- The 5 existing indexable pages were White Noise, Pink Noise, Brown Noise, Rain on Window and Fireplace.
- Of 17 noindex pages, **16 already had owner-approved audio**; Green Noise remains separately pending real-device approval.
- All 12 recent owner-approved synthetic DSP pages contained an obsolete "human listening acceptance pending" QA label. Several existing sound pages linked to CC0 files with obsolete "short recording awaiting review" descriptions.
- **Four real CC0 field-source pages** (Box Fan, Heavy Rain, Ocean Waves, Waterfall) were only about 288–312 words, without per-page A/B comparison or FAQs. The underlying approved source lengths were 67.52s, 189.76s, 89.83s and 375.48s.
- No GSC query demand, ranking data or third-party keyword volumes were used to select the pilot. This is an **editorial technical audit**, not evidence that Google has indexed or ranked the pages.

## Pilot actions

All four field Sound Pages received:
- a unique, source-specific explanation, true source duration, original author/license attribution, an audio-facts table and a transparent repeating-loop disclosure;
- four instant A/B choices linked to independently existing source IDs, four page-specific FAQs, accessible active-source feedback and useful internal links;
- continued playback with the **existing unchanged** Safari HLS and MP3 fallback player. No new sound ID or master, re-encoding, HLS regeneration, or changes to the 45 preset mixes.

**Selective indexing policy:** Heavy Rain (3:10 natural source) and Waterfall (6:15 natural source) are added to the sitemap and allowed to index **after passing all QA**. Ocean Waves (1:30) and Box Fan (1:08) receive the same UX upgrade but remain `noindex,follow` pending consideration of longer independently recorded source material. This gate is an editorial heuristic, **not** a Google threshold or proof that short recordings cannot rank.

After the pilot, intended state is **7 indexable Sound Pages, 15 noindex**, and **15 sitemap URLs** overall (13 existing + Heavy Rain + Waterfall).

## Inventory and next-stage decisions

| Sound page | Audio review | SEO status after pilot | Decision / next work |
|---|---|---|---|
| White Noise | Previously accepted | Indexable | Retain established reference page |
| Pink Noise | Previously accepted | Indexable | Retain established reference page |
| Brown Noise | Previously accepted | Indexable | Retain established reference page |
| Green Noise | Pending separately | Noindex | Keep blocked until listening approval |
| Blue Noise | Owner-approved | Noindex | Verify standalone query intent and differences to Violet |
| Violet Noise | Owner-approved | Noindex | Confirm unique intent vs Blue and White |
| Soft White Noise | Owner-approved | Noindex | Strengthen differentiation vs White/Pink; avoid overlapping intent |
| Deep Brown Noise | Owner-approved | Noindex | Compare vs Brown and Low Rumble |
| Warm Pink Noise | Owner-approved | Noindex | Distinguish from standard Pink and relaxation collection |
| Neutral Mid Noise | Owner-approved | Noindex | Clarify natural search intent and distinct spectrum |
| Desk Fan — Synthetic | Owner-approved | Noindex | Compare with real fan; avoid implying physical recording |
| Box Fan — Field Recording | Owner-approved | **Noindex** | Upgraded; find longer independent source for further review |
| Rain on Window | Previously accepted arrangement | Indexable | Retain established reference page |
| Heavy Rain | Owner-approved | **Indexable** | Upgraded pilot; 189.76s verified independent CC0 recording |
| Ocean Waves | Owner-approved | **Noindex** | Upgraded; source is only 89.83s, assess longer CC0 alternative |
| Waterfall | Owner-approved | **Indexable** | Upgraded pilot; 375.48s verified independent CC0 recording |
| Shower — Synthetic | Owner-approved | Noindex | Keep independent of Waterfall/Heavy Rain intent |
| Gentle Wind — Synthetic | Owner-approved | Noindex | Avoid mislabeling synthetic wind as a nature recording |
| Fireplace | Previously accepted arrangement | Indexable | Retain established reference page |
| Airplane Cabin — Synthetic | Owner-approved | Noindex | Evaluate standalone transport ambience intent |
| Air Conditioner — Synthetic | Owner-approved | Noindex | Compare fan/AC realism before promotion |
| Low Rumble | Owner-approved | Noindex | Avoid broad near-duplicate hum/noise pages |

## Integrity and release rules

1. `scripts/test_field_sound_pages.cjs` enforces CC0 author/source URL, source/master SHA match, accurate AudioObject duration, accessibility, canonical, content quality, no-autoplay, comparison IDs, 7/15 index policy and 15-URL sitemap.
2. `scripts/test_field_sound_browser.cjs` tests all four pages in a browser with 390px and 320px layouts, A/B switching without navigation, Sleep Timer deadline preservation, persistent playback on SPA navigation, and native MP3 controls without JavaScript.
3. Existing `player_smoke` regression continues to validate the 22-source player, 45 mixes, old Sound Pages and 3 finished intent collections.
4. An audio-approved status is **not** permission to bulk-index. Maintain Green Noise noindex. User listening approval does not imply medical claims or hearing-safe playback levels.
5. Do not declare production LIVE until GitHub Pages deployment succeeds and the public URLs actually serve new content.
