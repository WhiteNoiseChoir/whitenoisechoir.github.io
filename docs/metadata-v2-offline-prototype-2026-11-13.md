# WhiteNoiseChoir — Metadata V2 prototype (read-only)

## Scope and upstream evidence
- This branch introduces a canonical JSON Schema, offline sidecar converter and tests. It does not change Studio engine, UI, presets, deploy, R2, secrets or production data.
- Audit Draft PR #79 established 86 legacy Studio catalog slots and a stable SHA/reference-ID strategy. A GitHub Actions catalog publish (run 43344568755) recorded 21,698 unique R2 SHA assets and 21,674 indexed. Exact causes of 24 exclusions remain unverified because the private sidecars were not accessible.
- `r2-<SHA256>` is the content-addressed ID; when derived from R2 object path alone its basis is flagged **unverified**. `legacy-key-<SHA256(UTF8-key)>` and `legacy-url-<SHA256(UTF8-url)>` are reference IDs, not audio byte checksums. Preserve all 86 legacy positions and old JSON references.

## Two-tier intake design

**Tier 1: fast intake.** Acquire only authorized source bytes. Probe with ffprobe; calculate real byte SHA-256, deduplicate, retain license/attribution evidence, store immutable original in private R2 and verify read-back before changing lifecycle from `discovered` to `stored`. Keep source sidecars. Validate every normalized V2 JSON before indexing. Avoid re-uploading or modifying existing bytes.

**Tier 2: semantic enrichment.** Use asynchronous priority batches by production demand (nature, winter, wildlife, instruments). Extract audible entity, continuous-bed/event role, environment, near/far, intensity, mood, loopability and real measured LUFS/peak. For music, BPM/key/chords/time-signature require a measurement or verified source; otherwise remain null. Label measured/verified/inferred/unknown and preserve evidence and confidence per field. Never promote to `mix_ready` without rights, storage and QA checks. Allow re-enrichment without changing asset ID.

## CLI and tests

```sh
python -m pip install 'jsonschema>=4,<5'
python -m unittest discover -s scripts -p 'test_normalize_audio_metadata_v2.py' -v
python scripts/normalize_audio_metadata_v2.py --input /private/input.json --output /private/metadata-v2.json
```

Input may be a JSON array or an object containing `assets`, `items`, or `rows`. Output contains V2 records, counts and row-level errors. Conversion is offline and read-only except for the output path explicitly supplied. Schema violations return process exit code 2. Existing metadata rights flags are recorded as **attested**, not independently verified. Converter does not claim audio exists in R2. Unknown attributes are null, never invented. Duplicate IDs collapse in this prototype; production dedup must preserve additional independent provenance claims rather than discard them.

**Known limitations:** This is not a running scraper integration, audio classifier, real R2 migration or Studio integration. The prototype does not hash actual bytes, measure audio metrics, validate license evidence independently or preserve duplicate provenance. It needs independent QA on real records before any rollout.

## Compatibility gates for AI Audio Director
- `assetRef` supported in current Studio expects `r2-<sha256>`; do not send `legacy-key`/`legacy-url` values as `assetRef` without a separately approved compatibility resolver.
- Old projects still reference numeric `asset` slots; never reorder or drop the 86 baseline slots.
- Director must preflight R2 availability, permissions, semantic suitability and temporal constraints before generating existing Studio JSON; never invent IDs.
- No merge, deploy, live data processing, workflow edits or R2 writes without owner approval.

## QA expected before production
1. Dry run on 100–300 real sidecars from multiple source families with sensitive data omitted.
2. Verify 24 exclusions by SHA/reason from R2 using read-only credentials; avoid leaking private sidecars into public logs.
3. Confirm 86 legacy mapping, output idempotence, duplicate provenance, old project import, 45 presets and Studio browser playback in isolated staging.
4. Evaluate semantic/music reliability and per-field evidence. Release only after owner explicitly approves.
