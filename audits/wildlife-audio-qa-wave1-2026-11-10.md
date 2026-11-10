# Wildlife Wave 1 — QA intake and blocker audit
Date: 2026-11-10

## What was verified directly
Freesound public pages for 639984, 745273, 857163 and 510502: duration, file type and page-labeled CC0. Original download requires an authenticated Freesound account. Full source bytes were **not** obtained; no listening QA, independent audio duration verification, SHA256, true peak or HLS test has occurred.

## Explicit concern
The Goldenboy76 crickets recording (857163) includes a public reviewer comment reporting recorder movement and possible conversation despite the upload description advertising no sudden noise. Its WREC-005 intake priority is HOLD until actual inspection.

## Proposed QA queue
1. WREC-002 Dawn Chorus (613.75s FLAC)
2. WREC-003 Coniferous Forest Bird Chorus (589.097s FLAC)
3. WREC-006 Night Crickets alternative (346.302s WAV)
4. WREC-008 Frog Pond (256.009s MP3, already looped source)
5. WREC-005 Night Crickets first candidate — HOLD because of reported contamination

## Actual intake
After authorized Freesound login, put source files on a local workspace named `WREC-002.flac`, `WREC-003.flac`, etc. Run:
```bash
node scripts/wildlife_audio_intake.cjs
node scripts/wildlife_audio_intake.cjs /path/to/WREC-002.flac
```
Requires `ffprobe` (ffmpeg). Results include file SHA256 and probed duration/streams, but do not constitute release approval. Preserve results with source provenance.

## What must still happen
Source download, verify license/authorship and file identity, inspect waveform/events, human audition, continuity and 10min loop QA, approved MP3 generation, upload to review storage, review page with seek bar and mobile QA, owner approval. No player changes, HLS modifications, MP3 changes, SEO URL changes or publish to production in this PR.
