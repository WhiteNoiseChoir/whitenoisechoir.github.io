# Water & Ocean Wave 3 — source-page verification gate

**Date:** 2026-11-09  
**Base production:** `d975d801485c5bac8d54849846d5aaa62cd14643` — 35 sources / 35 HLS / 45 presets.  
**Status:** Research-only. **No media downloaded, no 600s master built, no listening approval, no production change.**

## Decision after first sourcing pass

Only NEW-33 (Pond Ambience) has **metadata-level** prospects longer than 605 seconds. These are *not* ready for owner audition yet. All other NEW-11/31/32/34/35/36 remain blocked or unsourced. Direct, independently long sound recordings take precedence over short clips stretched or repeated and given a new name.

- **NEW-33 Pond Ambience:** `rebelgirl2006_tiger/345600` — 608.013s, stereo 24 kHz, CC0; pond frogs/birds with recorded occasional cars and wind. Meets *declared duration only*. Potentially noisy/low bandwidth. Alternative `felix.blume/868745` — 791.167s, stereo 48 kHz, CC0; explicitly frogs/toads/crickets at a French Guiana forest pond, **not proof of flowing or lapping water**. Screen possible Nature-family placement.
- **NEW-31 Mountain Stream:** authentic Welsh mountain-stream sound `squashy555/331894` is only 156.192s; Alberta mountain-stream sound `Auxide_Audio/585497` only 32.622s. Longer Oxfordshire riverside `chris_dagorne/348177` (869.543s) is *not mountain stream* and includes road/motorbike and birds. Block mountain-stream label.
- **NEW-32 Lake Waves:** Lake Ohrid `jazbavac/198521` 334.391s, Lake Pymatuning `Mick_/705034` 204.973s, and `kvgarlic/326097` 93.882s. All CC0 but below the 605s independent-source gate. Do not fake ten independent minutes.
- **NEW-34 Zen Fountain:** `skyko/169252` ~61s generic fountain; `vhio/789097` ~430s public square with speech and traffic. No validated authentic quiet zen fountain with adequate independent duration.
- **NEW-11 Bamboo Fountain:** original hold is still correct; no authentic long CC0 shishi-odoshi has been qualified.
- **NEW-35 Running Sink / NEW-36 Hot Tub Water:** no qualified source-page candidate in this pass.

## Required gate before ANY review MP3

1. Fetch a candidate's actual Freesound media / high-quality preview and verify its accessible duration, sample rate, channels and checksum. A Freesound metadata page is not proof that a preview provides all 605 seconds.
2. Listen for accurate acoustic identity, traffic, people, wind, abrupt edits, bird prominence and differences from the 35 live sources. Record reject/relabel decisions.
3. If material is suitable, build a **genuinely 600s**, 44.1 kHz stereo 192 kbps MP3 (upmix disclosed; resampling never described as restored fidelity) from at least 605s of independent content, verify seam and FFprobe; do not synthesize missing independent material.
4. Publish a **noindex review-only** lab and verify public audio links and mobile playback. Obtain explicit approval per source before introducing an HLS stream, updating catalog/roadmap production state, or adding pages.
5. Preserve existing URL canonicals, 45 presets, original 35-source audio hashes and sitemap 18 URLs; do not index new variant pages on release by default.

## License and provenance policy

All candidates in `catalog/water-ocean-wave3-candidates.json` have license **declared** by their Freesound pages as CC0. No local copyright-asset or source fingerprint verification has occurred; the manifest explicitly separates declared metadata from audio QA. Excluded lake examples with CC BY are not considered eligible under the current CC0-only intake rule.

This note is an audit record, **not** evidence of listening approval, technical PASS, iPhone lock-screen QA or production deployment.
