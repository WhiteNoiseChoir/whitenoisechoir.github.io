# WS5 — Acoustic Intelligence · phase 1 · 2026-11-14

## Intent
Objective is **automatic** acoustic signal analysis of real R2 originals to help select relaxation/sleep soundtracks without forcing user to listen to each source.

## Processing and provenance
- Runs independently on GitHub Actions hourly at minute 37 UTC; 24 candidates/run maximum and 50 scanned. No changes to WS2/WS3/WS4.
- Reads canonical WS1 SQLite from R2 via `internal/ai-metadata-index/v1/current.json` and verifies whole-index SHA; prioritizes water/rain/wind/forest/nature/animals. Excludes metadata-only music until an actual R2 object is imported.
- Only supports verified content-addressed R2 object keys under the four audio-intake prefixes. Each source is downloaded only if <=16MB. Original file SHA256 checked before analysis.
- Three 25s decode windows at start, middle and near end (or one window for short sounds). FFmpeg decodes 16k mono; NumPy measures RMS, sampled peak, silence fraction, 100ms RMS jumps, peak-to-RMS, spectral centroid and high-frequency energy.
- All output is stored under R2 **private** `internal/ws5-acoustic-intelligence/v1/source-<ws1sha16>/`. One SHA-based record each, small batch summaries, checkpoint. Never overwrites original audio or any Studio project.
- Full-file auditory content identification is **NOT** included. This phase does not automatically identify speech, animals, music, fatigue or true sleep suitability. Those fields are explicitly NOT_RUN/UNVERIFIED. Heuristic `NO_FLAG_IN_SAMPLED_WINDOWS` is not user approval.
- Only 16MB maximum files are analyzed in phase 1; larger objects are flagged SKIPPED_LARGE. Any error recorded, not misrepresented as successful.
- Checkpoint resumes after each batch. A new canonical WS1 version creates a new checkpoint; previous R2 metrics remain untouched.
- Pacing: max 24 files per hourly run, one concurrent run at a time to avoid heavy download/CPU pressure alongside WS2/WS3/WS4.

## QA and next phases
1. Confirm initial 24-file pilot, validate checkpoint counters, false-positive spikes and download volume.
2. Integrate verified WS5 metrics into GitHub Private metadata bridge so ChatGPT sees acoustic evidence alongside WS1/WS2 (do not expose private rows in public repo).
3. Phase 2 add explicit sound-event and speech/music classifiers (requires running tested models) and high-confidence, carefully calibrated sleep/relax ranking. Review samples for reliability before rollout.
4. If 16MB limit excludes important long ambiences, develop streaming/segmented decoding with measured R2 transfer budget.

## Safety
Do not claim WebAudio playback success, rights to publish, or owner listening approval from the WS5 metric. Preserve every existing file and mix. Retain full SHA and external provenance from WS1/Studio.

## Status
Source code and workflow PR include unit tests. The first R2 acoustic run requires passing the merge activation workflow; log metrics verify only batch counts, not individual private file content.