# WhiteNoiseChoir audio library — public beta

There are **21 user-selectable sound sources** in the player:

- 15 original synthesized noise / ambient-demo MP3 files;
- 6 distinct real-world field recordings, sourced from Freesound and marked **CC0 1.0** by the respective uploaders.

Recording filenames end in `-real.mp3`; synthetic prototypes keep their original filenames.

Each original CC0 page, creator, source preview, content checksum and processed filename is documented in [cc0-sources.json](cc0-sources.json) and on the [public license page](https://whitenoisechoir.github.io/sources.html).

Three foundational colored noises — **White Noise, Pink Noise and Brown Noise** — are independently synthesized original **10-minute** stereo (centered dual-mono), 44.1 kHz, 192 kbps MP3 masters. They do not use repeated 60-second samples. Their encoded spectral slopes, LUFS, true peaks, 10-second loudness drift, loop-boundary estimates and SHA-256 hashes are recorded in the [color master manifest](color-master-manifest.json). Human long-form listening review is still pending. The other **12 synthetic tracks** (Blue, Violet, Soft White, Deep Brown, Warm Pink, Mid, Low Rumble, Desk Fan, Air Conditioner, Airplane Cabin, Wind, and Shower) have independently generated original 10-minute 44.1 kHz, 192 kbps stereo masters. Every final MP3 passed technical QA and has a recorded hash, LUFS, true peak, spectral fingerprint and boundary diagnostic in the [extended DSP manifest](extended-dsp-manifest.json). These are correctly labeled synthetic; human sound-identity and comfort checks are pending.

Four original CC0 demo recordings remain approximately 54-second stereo loops. Rain on Window and Fireplace now use 10-minute, 44.1 kHz stereo, 192 kbps MP3 extended listening masters built from their separately user-approved 60-second Signature samples. Each ten-minute master reorders segments from the same original one-minute recording with gentle crossfades; this does not provide ten minutes of unique field recording. See [production master manifest](master-manifest.json) for final SHA-256, source checksum, and final encoded MP3 QA. No recordings were copied from YouTube.

**Quality control:** The original issue was that many nature tracks were different filters of broadband noise. The five prominent nature/machine tracks were replaced with independent field recordings. The remaining simulations are intentionally labeled as synthetic and need further listening review. The 60-second source samples of Rain and Fireplace were user-approved, and the ten-minute masters have passed technical QA; their long-form iPhone looping and sleeping comfort have NOT yet been human-approved. The twelve new synthetic masters and four short CC0 recordings require full human listening QA. The source-length provenance of the four short recordings is documented in [field source audit](field-source-audit.json). Original recordings are being prepared for separate listening approval, not silently promoted. The 10-minute color-noise masters are original algorithmic audio rather than third-party field recordings.
