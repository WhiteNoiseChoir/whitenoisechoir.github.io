# WhiteNoiseChoir — Studio Intent + Frequency + Baby upgrade v1 (2026-11-16)

## Owner intent and roll-out constraints
- Original composition remains 600 seconds by default. Long-form YouTube is produced in the separate rendering pipeline.
- Primary production strategy stays approx. **70% Relaxing Nature + Music / 30% diversity**, including Meditation, Frequency, Baby Sleep, Focus and noise.
- **Search private metadata first**, choose concept broadly, and only then map to verified real source assets, provenance and rights before publication.
- Preserve all old Studio projects, the 15 legacy source slots, append-only Studio catalog, existing R2 originals and video preview/export. Never expose private metadata in public code.
- All Baby and Frequency labels describe the *audio signal* or potential listening context; neither is medical effectiveness or hearing-safety certification.

## Implementation
### Left library: intent-aware discovery
- Intent: All / Sleep / Relaxing / Meditation / Focus / Baby Sleep & Calming.
- Context-sensitive style (e.g. Meditation: sound bath, drone, nature, frequency; Baby: steady noise, calming, lullaby, gentle nature).
- The UI filters **available Studio catalog entries**, not the private 22k research records. Results are relevance candidates, not listening QA or publication approval.
- Legacy search, group filter, preview, timeline drag/drop, Inspector and video controls remain intact.
- Baby 600-second demo: low mix gain, pink noise and gentle rain. Not automatically approved for infant use.

### Frequency synthesis integrated into Studio
- Local PCM WebAudio, **not fake assetRef or R2 content**.
- Pure (sine), binaural (L/R separately), monaural (both beats mixed to each channel) and isochronic (periodic amplitude).
- Carrier: 40–1500 Hz in 0.1 Hz steps. Beat: 0.5–30 Hz in 0.1 Hz steps; binaural requires headphones for intended dichotic effect.
- Synthesized buffers use 44.1/48 kHz native context rate, 10-second coherent loops; 10-second period is exact for frequency multiples of 0.1 Hz. Displayed synthesized source plays and exports through the same clip schedule, gain, pan and high/low-pass processing used for R2 sources.
- Default synthesis gain deliberately low and must still be evaluated at the listener device. No effect/therapy claim.
- In Baby discovery mode, creation of frequency layers is disabled by UI. Baby project export also requires acknowledgment of unverified hearing safety.

### Stable JSON source identity
- Downloaded project JSON now has `assetKey` for catalog/legacy files, `assetRef` when the key contains a real SHA and `generated` only for local synthesis.
- Import prioritizes `generated`, then SHA `assetRef`, then exact `assetKey`, finally legacy numeric `asset` for backward compatibility.
- Legacy numeric-only JSON warns user to validate Inspector identities. **No silent guessing / automatic substitution** by track label.
- Max 32 tracks, Undo/Redo, parameter shapes and existing numeric legacy references are preserved.

### Inspectors and mix QA
- Verified wiring (source code): start, gain, offset, duration, fadeIn/fadeOut, pan/panEnd, highpass/lowpass; mute, loop, Solo, duplicate and delete. Solo is preview-only. Fade per side cannot exceed half clip duration; gain is not LUFS normalization.
- Browser regression tests validate source selection, Baby demo, generated stereo signal, JSON export/import and six-second WAV export.
- Audio diagnostics distinguish source loading from errors, but full owner listening QA and actual SPL on a physical output device remain outside browser automation.

## Private metadata and acoustic measurement
- WS1 canonical metadata count in 2026-11-16 snapshot: 22,239 (19,680 nature, 2,559 music candidate). Counts may change; do not hardcode operational progress.
- Private exporter adds lexical `intent_candidates`, `baby_intent_candidates`, `frequency_method`, `frequency_declared_hz_candidates`, `source_availability`, and explicit `frequency_verified:false`, `binaural_stereo_verified:false`, `baby_audio_qa:NOT_ASSESSED`.
- WS5 sampled mono 16 kHz descriptors now include *approximate* spectral peak, high-band energy and RMS variation. This **does not** verify exact pure tones, binaural beats or safety at an infant's ear.
- Only private canonical metadata exporter writes rows into WhiteNoiseChoir/wnc-metadata-index; never expose R2 private rows in Public GitHub Actions logs/artifacts.
- WS2–WS6 automation prompts are extended without modifying schedule/enabled flags; still require checkpoints, source evidence and no speculative QA approval.

## Release gates / known follow-ups
- Test in Chrome with headphones and compare preview vs WAV (gain, pan, fades, mono downmix).
- Manual check imported old JSON: numeric-only assets are **not stable across reordered catalogs**; use newly exported JSON with `assetKey`/SHA whenever possible.
- Frequency analyzer is a **sampled descriptor**; true stereo carrier verification after YouTube transcode is not built in this version.
- Baby: do not claim safe SPL based solely on the file. Keep speakers away from the crib, use low volume and limit playback according to pediatric guidance. Avoid shock, bright transients, loudness jumps and autoplay all night as defaults.
- Future sound conflict scoring, detailed device QA, dedicated post-YouTube audio comparison and advanced creative sound journeys require separate validated phases.

## Rollback and verification
- Feature branch: `feature/studio-intents-frequency-baby-20261116`.
- QA: `.github/workflows/qa_studio_intent_audio_v1.yml`, `scripts/test_studio_intent_frequency_v1.cjs`, `scripts/test_studio_intent_browser.mjs`, existing WS5 and private bridge offline tests.
- No modification of `studio-catalog.js`, existing JSON projects, video backend or actual R2 originals is required for this feature.
- If runtime regression is found after deployment, revert the merge commit and rebuild Studio route cache, without touching sound catalog or audio bytes.
