# WhiteNoiseChoir Signature Collection — Listening QA Protocol (Batch 01)

**Status: 10 selected audition tracks. Not approved production masters.**

## Intended uses
- Colored noise: white / pink / brown for masking, rest and focus.
- Environmental recordings: rain on window, heavy rain, ocean, box fan, air conditioner, fireplace, forest drips.
- These recordings are *not* medically validated treatments and are not automatically approved for use by babies.

## Automated technical checks
Each 60-second stereo 44.1 kHz MP3 at 192 kbps is decoded after encoding to verify:
1. Decoded duration is at least 59.5 seconds;
2. No clipped samples, with sample peak below full scale;
3. RMS and sample peak are reported in dBFS;
4. No prolonged unexpected digital silence;
5. Loop-boundary sample jump relative to ordinary adjacent-sample changes is estimated;
6. Power-spectrum slopes of white / pink / brown are checked against 0 / -10 / -20 dB per decade, tolerance ±7.
7. Crest factor = decoded MP3 sample peak minus overall RMS (both dBFS), reported for each audition sample. Rain on Window and Fireplace must remain at or below 25 dB.
8. For Rain on Window and Fireplace, FFmpeg EBU R128 measures **integrated loudness (LUFS)** and **true peak (dBTP)** on the *encoded MP3*: acceptance ranges are −38 to −18 LUFS and true peak ≤ −1 dBTP. Their RMS must remain within −32 to −22 dBFS; unexpected 250 ms silent windows, clipping, and boundary jumps continue to be checked.
9. SHA-256 values of all ten final MP3s must agree with the manifest. A prior v2 remaster is **audited without re-encoding**; only recognized v1 input hashes may be remastered. Full ten-track builds are manual-only and regenerate the two remasters from hash-pinned original field recordings.

LUFS and RMS characterize delivered digital audio, **not the physical sound-pressure level** at a person's ear. They do not establish volume safety for infants or children.


These checks are useful but **do not prove** correct sound identity, naturalness, comfort or a gapless MP3 loop on iOS. A technical PASS is not an editorial approval.

## Human QA checklist
For EACH track:
- Headphones: audible sound character matches label; no distracting crackles or sudden voices.
- iPhone speaker: no irritating treble or excessive harshness. Keep a low starting volume.
- Listen from 50 to 65 seconds to check looping and MP3 encoder boundary behavior.
- Switch White → Pink → Brown and confirm a meaningful spectral difference.
- Compare Rain on Window → Heavy Rain → Ocean and Box Fan → Air Conditioner: these must sound genuinely different.
- Observe the presence of thunder, birds, crackles or other transients and decide whether they are appropriate for adult sleep vs relaxation.
- Lock the iPhone with audio playing; verify it continues, controls work, and no unintended source switching happens.
- Rate 1–5, explain failed sounds, export the saved review JSON.

## Review decisions
- **1–2:** reject / replace source.
- **3:** modify EQ, dynamic range or choose another portion; re-audition.
- **4:** suitable prototype; create longer master and re-test.
- **5:** strong source candidate; still requires full-master listening QA.

## Production promotion gates
1. Sound identity and playback comfort human-rated >=4.
2. 100% technical checks passed or deviations documented and accepted.
3. A longer seamless master is produced and evaluated, preferably with >10 minutes of independent environmental variation.
4. Source / license provenance captured in machine-readable manifest; no direct YouTube rips.
5. Main player has tested background playback on mobile and explicit errors for unavailable recordings.
6. Baby-specific use requires separate pediatric sound-level and duration constraints.

**Do not silently replace the 20 existing public library sounds.** All audition assets are isolated under /signature/.
