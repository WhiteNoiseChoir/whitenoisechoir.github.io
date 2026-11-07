# WhiteNoiseChoir audio library — public beta

There are **21 user-selectable sound sources** in the player:

- 15 original synthesized noise / ambient-demo MP3 files;
- 6 distinct real-world field recordings, sourced from Freesound and marked **CC0 1.0** by the respective uploaders.

Recording filenames end in `-real.mp3`; synthetic prototypes keep their original filenames.

Each original CC0 page, creator, source preview, content checksum and processed filename is documented in [cc0-sources.json](cc0-sources.json) and on the [public license page](https://whitenoisechoir.github.io/sources.html).

Four original CC0 demo recordings remain approximately 54-second stereo loops. Rain on Window and Fireplace now use 10-minute, 44.1 kHz stereo, 192 kbps MP3 extended listening masters built from their separately user-approved 60-second Signature samples. Each ten-minute master reorders segments from the same original one-minute recording with gentle crossfades; this does not provide ten minutes of unique field recording. See [production master manifest](master-manifest.json) for final SHA-256, source checksum, and final encoded MP3 QA. No recordings were copied from YouTube.

**Quality control:** The original issue was that many nature tracks were different filters of broadband noise. The five prominent nature/machine tracks were replaced with independent field recordings. The remaining simulations are intentionally labeled as synthetic and need further listening review. The 60-second source samples of Rain and Fireplace were user-approved, and the ten-minute masters have passed technical QA; their long-form iPhone looping and sleeping comfort have NOT yet been human-approved. Other tracks also require full human listening QA.
