# Wildlife Source Discovery Wave 2 — Wikimedia Commons
Date: 2026-11-10

## Outcome
- **4 distinct file-page candidates**, covering **3 Wildlife archetypes** (Dawn Chorus, Crickets at Night, Frog Pond).
- Wikimedia provides public direct download links, but original media bytes have **not yet been acquired or measured** in this pass.
- All four files display **CC BY-SA 4.0**, not CC0. Commercial reuse is possible subject to exact license terms, but obligations must be assessed for standalone sound streaming, re-encoding and edits before publication.
- One duplicate entry intentionally excluded. Never count aliases as new MP3.

## Reviewed pages
- WREC-015: [Crickets choir](https://commons.wikimedia.org/wiki/File:Crickets_choir.ogg), 1304.404s, OGG Vorbis, CC-BY-SA-4.0, attribution Serg Childed; ShareAlike and attribution compliance; must listen for speech/event noise
- WREC-016: [Home Dawn Chorus 2020-04-28 0600](https://commons.wikimedia.org/wiki/File:Home_Dawn_Chorus_2020-04-28_0600.mp3), 622s, MP3 192kbps, CC-BY-SA-4.0, attribution Robert EA Harvey; Traffic contamination and license compliance
- WREC-017: [0426AM Dawn Chorus 07-May-2023](https://commons.wikimedia.org/wiki/File:0426AM_Dawn_Chorus_07-May-2023.ogg), 4053s, OGG FLAC, CC-BY-SA-4.0, attribution Alexander Wendt; Large acquisition footprint, noise, attribution/share-alike
- WREC-018: [Frogs croak calling chorus at night](https://commons.wikimedia.org/wiki/File:Frogs_croak_calling_chorus_at_night.ogg), 119.5805s, OGG Vorbis 53kbps, CC-BY-SA-4.0, attribution JogiAsad; Cannot claim 10min independent recording; bandwidth limitations

## Additional discovery
- [US Fish and Wildlife Service category](https://commons.wikimedia.org/wiki/Category:Audio_files_of_animal_sounds_from_the_United_States_Fish_and_Wildlife_Service) shows 26 public-domain tagged short wildlife recordings (wolf howls, waterfowl, shorebirds, woodpecker, alligator). Those are generally **seconds-long species-specific SFX**, not long sleep beds; each original provenance still needs verification.
- [Wikimedia Dawn chorus category](https://commons.wikimedia.org/wiki/Category:Dawn_chorus) lists 28 files with a range from seconds to hours; don't assume all licenses are identical.
- A Commons source licensing indicator is per-file, not a grant to rehost the entire category.

## Next actual QA
1. Obtain 1 permitted full source file (priority WREC-015) directly from Commons and compute SHA-256/ffprobe.
2. Inspect 10-minute continuous segment for speech or transient distractions, peak, loudness, loop seam and ambient suitability.
3. Generate audition MP3 only after rights review; save to separate review storage with native HTML5 seeking, not production R2 URL.
4. Obtain explicit owner listening approval before promoting any catalog record.

## Status
Research file only, not deployed. PRs #31–#36 are still separate research branches. This PR is stacked on #36, not merged into main.
