# WhiteNoiseChoir — Device and environment Sound Pages editorial release
Date: 2026-11-08
Scope: six existing independently synthesized 600-second masters. No modifications to MP3, HLS, JavaScript player, 45 presets or catalog IDs.

## Provenance / measurement
Data sources: `audio/extended-dsp-manifest.json`, `audio/review-queue-20261108.json`, `audio/continuous/manifest.json`, and `scripts/build_extended_dsp.py`. All six source IDs have technical PASS, owner listening APPROVED, duration 600s, 44.1 kHz stereo MP3/192kbps and independently generated DSP source material.

Measured spectral slopes are decoded-MP3 Welch estimates fitted over **120–6,000 Hz**, not exact descriptions of all frequencies or claims about real-world source acoustics. Five sampled digital amplitude-density bands are 80–250, 250–750, 750–2,000, 2,000–5,000 and 5,000–10,000 Hz. Each chart is normalized **within its own master**; do not read bar lengths as comparable absolute playback sound pressure, loudness or calibrated SPL. Four 20-second regions and 16,384-point Welch windows used in underlying source QA.

| Sound | Actual decoded-MP3 slope (dB/decade) | DSP-specific character | Index policy |
|---|---:|---|---|
| Desk Fan | −28.59 | 112/224 Hz low-level motor harmonics + filtered airflow, 2,650 Hz design LP | noindex |
| Air Conditioner | −45.25 | 60/120 Hz generated components + 1,900 Hz LP | noindex |
| Airplane Cabin | −35.28 | 87/174 Hz generated tones + 2,350 Hz LP | noindex |
| Low Rumble | −43.91 | Bass-weighted random texture + 280 Hz LP | noindex |
| Gentle Wind | −57.16 | 1,400 Hz LP, slow digital envelope | noindex |
| Shower | +15.69 | ~680 Hz high-pass, 10,500 Hz LP, bright water-like texture | **indexable pilot** |

LP = *low-pass filter*, not a physically measured appliance property.

## Interpretation and cannibalization review

- **Desk Fan / Air Conditioner / Cabin**: All were synthesized independently, but broad spectral-shape screening flags fan–cabin and AC–cabin similarity. AC is particularly close to Warm Pink Noise by normalized five-band spectral RMSE (1.91 dB). Different generator parameters do not guarantee distinct perceived listening experiences or search demand; retain noindex.
- **Low Rumble**: Narrowly bass-weighted DSP track overlaps Brown and Deep Brown Noise use cases. Better as an in-library listening comparison, noindex pending distinct intent validation.
- **Gentle Wind**: Original low-pass simulated airflow, not outdoor wind or leaves. Broad “wind sounds” demand may seek authentic field recordings; keep noindex. Removed the previously offered **unapproved Green Noise** instant-comparison choice, replacing it with approved Brown Noise. Green stays separately pending approval/noindex.
- **Shower**: Independent bright simulated running-water texture (+15.69 dB/decade over the fitted region), markedly different frequency balance from bass-weighted machine/noise beds. Specific indoor-spray intent differs from approved natural rainfall and waterfall pages. Good standalone editorial teaching value plus A/B comparison with field recordings; launch a *single, conservative indexable pilot*. This is an editorial hypothesis only: there are **no verified keyword-volume, GSC click, impression or Google index-status data** for this decision.

## Site changes

- Six existing canonical URLs, same MP3 and HLS bindings, five measured band visualizations each, tailored source-specific synthesis information, 5 FAQs each, retained in-page 4-source A/B, and appropriate AudioObject + WebPage + BreadcrumbList JSON-LD.
- Each page explicitly discloses original independent 10-minute synthetic source and continuous repetition after the master duration, no field-recording misrepresentation.
- Sitemap **17 → 18 URLs**, indexable sound pages **9 → 10**, noindex sound pages **13 → 12**. The three completed intent collections remain unchanged and indexable; four unready collections remain noindex. Green Noise remains noindex.
- `scripts/test_device_environment_editorial.cjs` guards actual source QA values, provenance, 5 bands, slope, source metadata, JSON-LD, canonical, no-autoplay, A/B, noindex and sitemap consistency. Existing test scripts updated for the precise single-URL selective release.
- `scripts/test_batch18_browser.cjs` adds 320/390px checks for the six chart pages, 5 FAQs, and Shower-to-Waterfall A/B with Sleep Timer and persistent navigation. Existing player-smoke and Batch18 workflows include the new test.
- No medical benefit, auditory safety, physical noise-pressure, recording authenticity, manufacturer-specific fidelity or proven SEO-rank claims are made.

## Release gate

Keep changes on `feature/batch18-device-environment-editorial-20261108` until the updated player-smoke and Batch18 QA workflows both pass. Confirm PR diff contains no changed audio files, audio engine, presets or catalog mappings. Merge only after passing, then verify GitHub Pages deployment success and the six public URLs/sitemap. `indexable` means the page permits indexing, not that Google has indexed it.
