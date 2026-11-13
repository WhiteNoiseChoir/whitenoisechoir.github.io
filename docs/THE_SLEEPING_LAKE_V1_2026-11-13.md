# THE SLEEPING LAKE V1 — 2026-11-13

## Intent and decisions
Relaxation / adult deep sleep, no music, no rain, no loud wildlife. Main bed: real CC0 Issyk-Kul shoreline waves. Secondary gentle wind: NPS Gem Lake. Distant ambience: park wind (tree species not established).

## Provenance and QA
- New CC0 original: https://commons.wikimedia.org/wiki/File:17650_thoschi_issyk-kul.ogg . Imported R2 SHA256 a512974fcff448950f86fa26d07fbb8d52b55e8cbdf24e8d721f42161a1d7f53; ffmpeg full decode; 224.392s; -30.36 sample LUFS; -1.29dBTP; R2 HEAD, 206/CORS verified. It is not a real pine-lake midnight recording.
- Existing R2 NPS Gem Lake wind: SHA256 aa4bd8042d04eb6b956bc1721fe6856145526bda5ff89edd8bc78559cd38451c; 271.434s; -33.11 sample LUFS; -4.53 dBTP.
- Existing R2 CC0 OpenGameArt park wind: SHA256 5c381856745b4706e7eba55eb9271a61a530e90c05df8126adb2db89ecfa6c5a; 256.803s; -44.04 sample LUFS; -15.61dBTP; species unknown.
- Rejected Yellowstone Lake candidate: 280.871s, measured -64.42 LUFS in 90s sample: too quiet to use unprocessed.
- Rejected Finch Lake long field recording: 2546.046s, risk of large browser decode and daylight background for deep sleep.
- CC0 pine forest recordings on Freesound were found but originals require login; no external preview was substituted.

## Browser and sound QA
- Headless Chromium WebAudio decode and CORS: separate CI on PR #94; must confirm before release.
- Dynamic mixing loudness and true-peak over entire 600-second timeline: not yet measured; source-level sample loudness does not replace mastering.
- No manual listening approval, no public export. All gain >= 0.37 with source-specific normalization limitations.
- Do not claim genuine pine needles: titles are artistic staging, not species verification.
- V1 trial route is noindex/nofollow; old presets and trials remain unchanged.
