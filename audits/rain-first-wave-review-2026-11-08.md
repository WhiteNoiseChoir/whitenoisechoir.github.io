# Rain & Thunder — first-wave listening review (2026-11-08)

**Status: REVIEW_ONLY; awaiting listening approval. Not published into the 22-source production player.**

Three CC0 source recordings are deliberately selected from independent creators to test real differences in acoustics:
1. **NEW-01 Light Rain** — joedeshon, long_easy_rain_08, 24:15.599 original. Freesound: https://freesound.org/people/joedeshon/sounds/430765/ ; HQ public preview: https://cdn.freesound.org/previews/430/430765_1218676-hq.mp3 . First ten minutes contain rain bed, subtle local ambient noise; reported distant thunder begins after ~16:20. Potential city/traffic contamination must be listened for.
2. **NEW-02 Rain on Tin Roof** — archerjosiah, Rain on Tin Roof – 1 Hour, 56:30.380 original, recorded inside a shed. Freesound: https://freesound.org/people/archerjosiah/sounds/843483/ ; public HQ preview: https://cdn.freesound.org/previews/843/843483_9671929-hq.mp3 . Distinct roof impacts must be checked against Rain on Window; no renamed rain source.
3. **NEW-06 Distant Thunder** — moxobna, 102610_distant_thunder_01.wav, 2:31.353 independent stereo source. Freesound: https://freesound.org/people/moxobna/sounds/107518/ ; HQ public preview: https://cdn.freesound.org/previews/107/107518_43834-hq.mp3 . A 10-minute audition **must repeat thunder events** when looping the short recording. This is explicitly disclosed and requires special human scrutiny.

All three are Freesound **CC0-1.0** per their public source pages (the individual source's CC0 metadata is the license evidence, not an extrapolation from other tracks). They are sourced from public *HQ MP3 previews*, not full original WAV files (which require account login). **HQ preview→192 kbps MP3 conversion is lossy transcode and cannot increase real source fidelity**. This is an audition stage only; production promotion requires high quality source decision and renewed listening signoff.

The isolated preview builder runs only in CI on a feature branch and publishes binaries under `/signature/rain-review/`; it does **not** modify `audio/`, the production HLS manifest, homepage inline player engine, preset recipes, `catalog/library.json`, Sound Pages or sitemap. The audition page uses a distinct native audio element and is explicitly **noindex,nofollow**.

Technical review checks: source preview must actually download, decoded stereo and bitrate reported, output 600s 44.1kHz stereo MP3, safe peak below -5.5 dBFS, source and output SHA-256, field provenance, explicit repetition counts, and output file duration. The audio still requires listening approval for character, dynamic peaks, frequency harshness, distracting traffic, repeated thunder, seam, device loop and volume.

Only after human listening: fetch original lossless/authorized source if appropriate, render real production masters, generate 7-day HLS, run the existing tests plus new-source tests, then activate each source in the registry/catalog. Decide SEO independently; no new sound detail URLs are authorized by merely passing technical audio QA.
