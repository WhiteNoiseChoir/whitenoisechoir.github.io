# Fast Sound Asset Intake — HIGH-VOLUME MODE
Effective 2026-11-10; follows asset-first WhiteNoiseChoir architecture.

## Product decision
The library must offer **many distinct audio choices to compose freely**. Stop treating every short audio event as a ten-minute mastered track. A 0.5-second bird chirp, a 4-second wolf howl, a 20-second train pass-by, and 2-minute stream ambience are all valuable in the mixer.

## Minimal fast-lane intake: 4 automated gates
1. **Rights/provenance**: one source record and per-file verifiable license evidence; proof of authorized download, website playback and remix permissions. Note: a boolean in a supplied manifest is an *attestation*, not independent verification. It should be populated by an authorized extractor/account or reviewed source mapping. Unclear rights go to review, not public release.
2. **File integrity**: supported media type, accessible local bytes, recognized audio stream, real duration >0 and SHA-256 checksum. No minimum 600 seconds.
3. **Exact duplicate suppression**: SHA-256 collisions/duplicates are not uploaded twice. Acoustic near-duplicates are low-cost asynchronous enrichment, not a per-file upload blocker.
4. **Basic metadata**: concept/entity, creator, audio role. Missing fields are flagged instead of blocking the entire batch.

**No mandatory human listening, ten-minute master, HLS conversion, individual editorial review, owner approval, waveform visualization, loudness normalization or SEO page for each clip.** Particularly important for wildlife and machinery one-shots. Perform deeper acoustic checks on flagged files and on featured/master compositions only.

## Status and user visibility
- `READY_FOR_STORAGE`: rights attested, file technically valid, exact SHA not duplicate. Batch uploader may place in private R2 and produce a playable preview rendition once rights/ACL are verified. **Not yet live/playable.**
- `NEEDS_REVIEW`: missing/uncertain rights, creator, category, or speech/vocal content. Quarantine individual file only.
- `DUPLICATE`: exact already-seen bytes; record extra provenance and alternate metadata without uploading duplicates.
- `REJECTED`: broken/unreadable, unsupported, empty or dangerous size.
- `MIX_READY` will be set **only after storage/upload verification and rights-safe delivery**, not by the intake script. Future user-authored YouTube export requires the `commercial_export_allowed` grant for every included clip.

This is strictly separate from SEO publication and replacement of the existing 35 production sounds. Keep 45 presets and player behavior stable.

## Running batches
Gather authorized source recordings and per-file license evidence. Do not commit files containing rights-controlled WAV/MP3 to public GitHub. Example manifest below is **illustrative only**; substitute actual file paths and verified source/license URLs.

```json
{
  "assets": [
    {
      "candidate_id": "wolf-howl-recording-001",
      "concept_ids": ["wolf-howl", "wildlife"],
      "role": "ONE_SHOT",
      "local_file": "/private/authorized-downloads/wolf-001.wav",
      "source_url": "https://source.example/sounds/recording-001",
      "creator": "Verified original creator",
      "rights": {
        "license": "CC0-1.0",
        "source_license_verified": true,
        "license_evidence_url": "https://source.example/sounds/recording-001",
        "verified_at": "2026-11-10",
        "authorized_download": true,
        "website_playback_allowed": true,
        "remix_allowed": true,
        "commercial_export_allowed": true
      }
    }
  ]
}
```

```sh
python3 scripts/fast_sound_asset_intake.py \
  --input /private/authorized-batch.json \
  --output /private/fast-intake-report.json
```

The tool reads local files, invokes `ffprobe` for metadata, streams SHA-256, deduplicates within the batch, and writes **JSON only**. It does **not** download sources, upload to R2, modify catalog, publish websites or render audio; no hidden "success" claims. It scales by batching manifests and keeping expensive quality analysis separate.

## Automatic collection later
Provider adapters should discover multiple source files per concept, verify license on each recording, download via authorized access/API into ephemeral storage, pass this fast lane, upload approved files to private Cloudflare R2, confirm object checksums, and then update a searchable public preview catalog for recordings whose licenses permit it. Do not use TinyFish browsing as a bulk audio downloader when a permitted provider API / authenticated original-download pipeline exists.

**Throughput should be measured as verified, deduplicated, usable files entering the user's mixer, not raw SEO candidate rows or workflow jobs returning success.**

## Optional QA, delayed/asynchronous
- Volume peaks/clipping, silence/gaps, distortion, source-specific loop seam, similar-sounding duplicates, speech/music detections.
- QA by sampling representative files in each new source batch instead of subjective auditioning every asset.
- Revisit suspicious batches, repeated errors, or reused sources; never override a failed rights gate because ingestion targets are high.

## Legacy compatibility
Existing C5/C6 long-master / owner-listening / release approval gates apply to the previously defined production release pipeline; do **not** block normal short-SFX intake with those older 605-second rules. Existing published sounds and search landing pages do not change in this step.
