# WhiteNoiseChoir — Noise Colors editorial release (2026-11-08)

This document records the editorial and source QA results for the six existing Noise Colors pages. This is not a ranking, keyword volume or Google indexing report.

## Verified independent audio

All six are **original 600-second DSP masters**, 44.1 kHz stereo 192 kbps, independently generated, SHA-pinned in `audio/extended-dsp-manifest.json` and previously approved for listening by the owner. Continuous HLS/MP3 looping is unchanged. Each page now uses its actual spectral-band measurements from `scripts/build_extended_dsp.py`; the plots normalize five frequency bands within the individual track, not to playback volume or sound pressure levels.

| Sound Page | Observed fitted PSD slope* | Convention | SEO release |
|---|---:|---|---|
| Blue Noise | +10.01 dB/decade | Ideal blue ~ +10; distinct sound, high-frequency weighted | **Indexable** |
| Violet / Purple Noise | +20.01 dB/decade | Ideal violet ~ +20; even stronger high-frequency weighting | **Indexable** |
| Soft White Noise | −6.70 dB/decade | Custom white-like broadband shaping, LP around 4,200 Hz | Remain noindex |
| Deep Brown Noise | −66.42 dB/decade | Highly bass-dominant custom sound; not textbook Brown (~−20) | Remain noindex |
| Warm Pink Noise | −41.65 dB/decade | Custom warm/dark variant; not textbook Pink (~−10) | Remain noindex |
| Neutral Mid Noise | −2.76 dB/decade | Custom mid-band profile; separate from Green | Remain noindex |

*The stated slopes are sampled decoded-MP3 linear fits over 120–6,000 Hz, not a claimed law holding across the full spectrum. Five chart bands: 80–250, 250–750, 750–2,000, 2,000–5,000 and 5,000–10,000 Hz. The source QA script uses Welch PSD estimation with 16,384-sample windows and samples four 20-second regions of each master.

### Why two indexed, four held

Blue and Violet Noise have independently well-defined theoretical frequency dependencies, meaning different engineering entities and directly contrasting sound files. We are testing two specific indexable pages only after individual content expansion. The remaining four pages remain available to listeners but noindex until their intent and distinct organic query demand can be established.

This selection is a conservative editorial judgment, **not** evidence from GSC, a Google minimum word count, an official duration threshold or a guarantee of indexing. We have no verified query-volume or click data for these six pages.

**Green Noise remains separately pending real-device listening acceptance**, noindex and absent from the approved Neutral Mid instant-play comparisons.

## Changes and preservation

- Six URLs keep their existing canonical paths and AudioObject sources, and each has 5 sampled frequency-band values, measured spectral slope, practical interpretation and 5 focused FAQs.
- The indexable Noise Colors hub adds the measured comparison table while the unapproved Green card stays transparently pending.
- Sitemap changes from 15 to **17 URLs**; indexable individual sound pages increase from 7 to **9**; the other 13 Sound Pages remain noindex. Existing 3 finished intent collections stay indexable.
- No MP3 files, HLS playlists, homepage player engine, 45 presets or other sound IDs are touched.
- `scripts/test_noise_colors_editorial.cjs` and `scripts/test_noise_colors_browser.cjs` gate content, audio IDs, measured numbers, accessibility, 320/390px layout, in-page A/B, timer persistence, navigation and MP3 fallback. Existing library and sound tests remain active.

Reference reading: [IEEE colored noise](https://technav.ieee.org/topic/colored-noise/) and [American Academy of Audiology: noise colors and volume](https://www.audiology.org/audiologists-know-about-noise-in-every-color/).
