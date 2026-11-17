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
- Manually dispatch the new workflow from **main** with `max_files=1–4` (default 2). It has **no schedule**, writes no GitHub artifacts and does not activate the model on PRs. The PR runs offline contract tests only. A one-off main-branch commit whose message starts with `feat(ws5): activate semantic pilot` additionally runs a **single file** after tests succeed; normal pushes never execute the model.
- Model: Hugging Face `laion/clap-htsat-unfused`, pinned revision `84bcbbd1d619e407a8216371ddef36e458d95d93`, CPU inference using Transformers 4.55.4.
- Source inputs: real nature audio files whose content-addressed R2 key matches a canonical WS1 record. No invented assets. SHA-256 of each original is verified before inference. Files above 16 MB are skipped; compressed originals are never overwritten.
- Audio is **decoded to mono 48 kHz**, using up to three deterministic **10-second windows** at beginning, middle, end. This differs from the 16-kHz v1 DSP path because the chosen CLAP model expects 48 kHz. Short files use a single window.
- Output: cosine similarity against a curated, versioned 20-prompt vocabulary (rain, water, wind, wildlife, fire, instrumental music, human speech, traffic, sudden sounds). These are **relative, uncalibrated model similarities**, NOT probabilities, definitive sound-event detection, real listening, or QA approval. Probable acoustic roles and contamination are explicitly unverified hints. Even a clean-looking result never clears speech, safety, rights or YouTube publication.
- Storage: private R2 prefix `internal/ws5-acoustic-intelligence/v2-clap/source-<ws1-sha16>/` with individual SHA records, batch JSON and an independently resumable checkpoint. Legacy v1 records/checkpoints under `.../v1/`, the Studio and original media are untouched.
- Logs print only aggregate batch counts/status, not source titles, object keys or individual model predictions. If the model cannot load, the run stops without moving the checkpoint.

### Rollout gates

1. CI must pass both v1 and v2 offline unit tests; inspect the code and PR.
2. Run **one** R2 source using the explicitly named activation merge commit (or manually dispatch from main); confirm model download/inference, actual 48 kHz sample decoding, schema and SHA verification. Inspect private sample-level predictions, failures and approximate CPU/R2 cost.
3. Pilot a diverse sample (rain, stream, birds, music if imported) and **manually validate** false positives/negatives, particularly speech/music. Calibrate category thresholds against labeled data before reporting probabilistic confidence or sleep suitability.
4. Only after measured success should an independent scheduled batch be considered. Do not copy private predictions into the public repository or trigger public publishing automatically. Music ingestion and the 16 MB long-file limit remain separate open work.
5. For larger scale, implement streaming/partial R2 access or bounded download, model caching, deduplication and checkpoint-level retry policy; verify real total cost before increasing concurrency.

### Rollback

Disable or remove `ws5_semantic_pilot.yml`. The v1 hourly workflow continues unchanged. V2 data is isolated in private R2; no cleanup or destructive migration is required.

## 17 Nov — WS5 schedule-resilience and diversified CLAP pilot

**v1 schedule best-effort mitigation.** GitHub Actions `schedule` can be delayed or dropped; no cron expression can guarantee a strict hourly service-level agreement. Keep the original `37 * * * *` as the primary opportunity and add `11 * * * *` as a backup opportunity. For scheduled executions only, `--min-gap-minutes 45` checks the authoritative versioned private R2 checkpoint `updated_at` before any candidate processing. If recent, it logs `WS5_ACOUSTIC_SKIPPED_RECENT`, changes no checkpoint and downloads no audio. Explicit manual dispatch bypasses cooldown. The existing 24-file limit and single-job concurrency remain, as do the canonical WS1 checksum and read-only source guards. Trigger an explicit v1 activation using the distinct `feat(ws5): activate acoustic v1` prefix; semantic activation must not trigger v1.

**v2 diversity pilot.** Keep the original one-file CLAP checkpoint and records exactly as they are. Use `--diversity-pilot` to start a **separate**, one-time sample at `internal/ws5-acoustic-intelligence/v2-clap/diversity-pilot-v1/source-<ws1sha16>/`. Candidates are taken only from verified canonical WS1 *nature* R2 audio. Sampling is deterministic round-robin by **metadata hints only** (rain/storm, freshwater, ocean, wildlife, wind/fire/fan, other); these are not ground-truth audio labels. Manual workflow permits 1–8 files; a merge explicitly titled `feat(ws5): activate semantic pilot` triggers one batch of 8. Maximum source download remains 16 MB per item, 48-kHz mono inference uses three 10-second windows; outputs and candidate identity remain private. **No recurring v2 inference schedule.**

**Validation limitations.** CI tests cover checkpoint cooldown/bypass/malformed timestamps and stratification determinism; real GitHub logs verify job execution and aggregate counts only. Report actual stratification counts and semantic scoring statuses, never an accuracy percentage without human-verified reference labels. CLAP similarities are uncalibrated and can be wrong; real recorded animal names and sleep suitability remain unverified. Preserve both v1 and original v2 checkpoints, model license and rights checks, original audio and the Studio.

**Next gates:** independently confirm scheduled v1 cadence over several hours (backup does not guarantee on-time GitHub delivery); check batch results of diversified v2; use small listening-evaluated examples to validate semantic precision and assess costs before enabling scalable classification.

## 17 Nov — CLAP eight-record post-inference audit

Source: eight-file stratified CLAP pilot in PRIVATE R2 `internal/ws5-acoustic-intelligence/v2-clap/diversity-pilot-v1/`.

- New one-shot gate: `.github/workflows/ws5_semantic_review.yml` and `scripts/ws5_semantic_review.py`. It reads canonical WS1 pointer, the original CLAP pilot checkpoint, its first eight-record batch and corresponding private SHA records. **No audio download**, no CLAP model invocation, no scheduled runs. Missing or stale source/checkpoints fail closed instead of guessing.
- Checks record SHA/source path, CLAP model+prompt-vocabulary revision, sample-window ranking, expected `NOT_APPROVED/NOT_VERIFIED` clearance and correct R2 versioned path.
- Evaluates weak *metadata-group* hints against the top CLAP labels. This is an **unverified agreement diagnostic**, not a measure of classification correctness; a dual-source soundscape could legitimately disagree. Flags unknown groups, possible contamination and changes of top match between windows, explicitly as *review needed*.
- Keeps a per-source review queue, titles, SHA, private R2 paths, CLAP similarity values and unresolved reference labels **only in private R2** `.../qa/v1/report-000000-000008.json`. GitHub logs show only aggregate counts. No upload of private artifacts to this public repository.
- Human reference truth, model accuracy, license checks, listening passes, sleep suitability and publication remain **UNKNOWN / NOT_APPROVED**.
- Rollback: disable `.github/workflows/ws5_semantic_review.yml`, or remove the audit script. The CLAP pilot source files, original records, earlier checkpoints and Studio are unaffected.

Next validation gates: inspect the audit counts from an actual R2 run; verify evidence quality on at least a few targeted audio clips through authorized listening, optionally use public CC0/CC BY audio with reliable reference taxonomy for an independently evaluated calibration set. Only then discuss an unattended 30–50-file semantic sampling pilot.

## Phase 2b — Independent AudioSet AST six-source QA (17 Nov 2026)

After the eight-record CLAP pilot audit (`WS5_SEMANTIC_QA`), **six records were flagged for further examination**. These six are NOT established as erroneous. A second independently trained AudioSet event classifier can provide complementary, **unverified** evidence.

- One-time, **no cron** workflow: `.github/workflows/ws5_ast_secondary_review.yml`. Script: `scripts/ws5_ast_secondary_review.py`.
- Pinned AST: `MIT/ast-finetuned-audioset-10-10-0.4593` revision `f826b80d28226b62986cc218e5cec390b1096902`, declared model license BSD-3-Clause. About 346 MB of safetensors weights; model downloads are restricted to this explicit run. This adds temporary CPU time and network cost; no permanent service is provisioned.
- **Exact six** flagged from `qa/v1/report-000000-000008.json` in private R2. The script fails closed if there are not between one and six flagged or if any record has already been marked as human listening PASS. It never touches nonflagged source files.
- For each file: verify strict original key/digest from report, R2 HEAD 16MB maximum, SHA-256 of downloaded original, ffprobe, sample three <=10-second windows from start/middle/end, mono 16 kHz. The original is read-only.
- AST returns AudioSet multi-label sigmoid scores, which are **not independently calibrated probabilities** and should NOT be equated to CLAP cosine similarity. Save ranked event hints, per-window hints, possible coarse event families and explicit `NOT_VERIFIED` status for speech, human listening, sound identity, license and sleep suitability. A second model's agreement is not validated accuracy.
- Output stays private under `internal/ws5-acoustic-intelligence/v2-clap/secondary-audioset/v1/source-<ws1sha16>/`, with SHA records and aggregate summary. Any GitHub Action log contains counts and possible broad family totals only: no private SHA/title/key/individual predictions. Nothing copied to Studio or private Music R2.
- There is no audio preview or human reference label yet. **Human-audition workflow must use an authenticated path**; never publish R2 objects or create publicly accessible raw preview URLs to bypass owner Access. The Music Access gateway has a separate bucket and permissions; it must NOT be treated as an authenticated Nature reviewer automatically.
- After a first run: compare results of both models as triage, establish a small human-verified reference set through authenticated listening, measure per-label precision/recall and cross-scene false positives. Only then increase CLAP throughput or automatically use semantic labels for Studio.

**Rollback:** remove/disable this secondary workflow. It does not alter original R2, v1 DSP, CLAP inference/checkpoint, private CLAP QA report, GitHub studio or public assets.

## Phase 2c — Cross-model private listening queue

After the 6-item independent AST run, create a one-time PRIVATE summary that joins the original CLAP audit with AST records by *exact verified SHA*. This does not establish sound identity.

- Workflow: `.github/workflows/ws5_cross_model_triage.yml`. Script: `scripts/ws5_cross_model_triage.py`; deterministic offline tests.
- Reads just the private eight-record CLAP QA report and six existing AST records. Refuses missing/duplicate SHA, noncanonical original R2 path, unverified source digest, unexpectedly approved status or nonflagged sources.
- Flags possible CLAP/AST speech and traffic warnings and temporal disagreement for prioritized **human review**, not automated content rejection. Priorities 1–4 are ordinal workflow order; they are **not calibrated confidence probabilities**.
- Creates one private, authenticated-only listening queue under `internal/ws5-acoustic-intelligence/v2-clap/secondary-audioset/v1/source-<ws1sha16>/human-review/v1/queue.json`. Each of six rows records SHA, title, labels/model scores, manual-review status, and up to three exact 10-second windows. Source paths are restricted to private R2, never public GitHub artifacts.
- This is NOT an audio playback or secure preview website. No original files transferred or copied. A future listener will need a properly authenticated access route before actual listening; do not assume the Music bucket's access gateway can read Nature R2.
- Model agreement/mismatch, rights/license clearance, sleep suitability, publication approval and **human reference accuracy** all remain unverified. Next step is authorized listening of these at most 18 short windows; use verified human labels to calibrate the broader semantic model.

Rollback: disable this one-shot workflow; no changes to Studio, source audio, CLAP checkpoints or AST source records.
