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
## Phase 2 — CLAP semantic pilot (17 Nov 2026)

**Status: code + deterministic tests added; live model/R2 evaluation must pass before any schedule is enabled.** The v1 hourly DSP job (minute 37 UTC) is unchanged.

- Entry point: `scripts/ws5_semantic_intelligence.py`. Workflow: `.github/workflows/ws5_semantic_pilot.yml`.
- Manually dispatch the new workflow from **main** with `max_files=1–4` (default 2). It has **no schedule**, writes no GitHub artifacts and does not activate on PRs. The PR runs offline contract tests only.
- Model: Hugging Face `laion/clap-htsat-unfused`, pinned revision `84bcbbd1d619e407a8216371ddef36e458d95d93`, CPU inference using Transformers 4.55.4.
- Source inputs: real nature audio files whose content-addressed R2 key matches a canonical WS1 record. No invented assets. SHA-256 of each original is verified before inference. Files above 16 MB are skipped; compressed originals are never overwritten.
- Audio is **decoded to mono 48 kHz**, using up to three deterministic **10-second windows** at beginning, middle, end. This differs from the 16-kHz v1 DSP path because the chosen CLAP model expects 48 kHz. Short files use a single window.
- Output: cosine similarity against a curated, versioned 20-prompt vocabulary (rain, water, wind, wildlife, fire, instrumental music, human speech, traffic, sudden sounds). These are **relative, uncalibrated model similarities**, NOT probabilities, definitive sound-event detection, real listening, or QA approval. Probable acoustic roles and contamination are explicitly unverified hints. Even a clean-looking result never clears speech, safety, rights or YouTube publication.
- Storage: private R2 prefix `internal/ws5-acoustic-intelligence/v2-clap/source-<ws1-sha16>/` with individual SHA records, batch JSON and an independently resumable checkpoint. Legacy v1 records/checkpoints under `.../v1/`, the Studio and original media are untouched.
- Logs print only aggregate batch counts/status, not source titles, object keys or individual model predictions. If the model cannot load, the run stops without moving the checkpoint.

### Rollout gates

1. CI must pass both v1 and v2 offline unit tests; inspect the code and PR.
2. Manually run **one** R2 source; confirm model download/inference, actual 48 kHz sample decoding, schema and SHA verification. Inspect private sample-level predictions, failures and approximate CPU/R2 cost.
3. Pilot a diverse sample (rain, stream, birds, music if imported) and **manually validate** false positives/negatives, particularly speech/music. Calibrate category thresholds against labeled data before reporting probabilistic confidence or sleep suitability.
4. Only after measured success should an independent scheduled batch be considered. Do not copy private predictions into the public repository or trigger public publishing automatically. Music ingestion and the 16 MB long-file limit remain separate open work.
5. For larger scale, implement streaming/partial R2 access or bounded download, model caching, deduplication and checkpoint-level retry policy; verify real total cost before increasing concurrency.

### Rollback

Disable or remove `ws5_semantic_pilot.yml`. The v1 hourly workflow continues unchanged. V2 data is isolated in private R2; no cleanup or destructive migration is required.
