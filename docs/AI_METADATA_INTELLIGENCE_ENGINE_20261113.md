# WhiteNoiseChoir — Metadata Intelligence Engine · Phase 1

**Owner intent (2026-11-13):** AI must be able to discover and select nature/wildlife/music recordings quickly from the existing R2 library. Expand metadata before downloading new media; preserve just-in-time audio intake by composition demand.

## Confirmed baseline
- Nature diversity source records: **19,935** R2 JSON documents as of the read-only inventory (pipeline source evidence with audio file references; not 19,935 unimported candidates).
- Canonical audio metadata: **20,607** R2 JSON objects, overlapping with source records.
- Music candidate metadata: **2,559**, not actual downloaded audio.
- Legacy editorial research catalog: **532** entries across 28 groups; core 7 nature families sum to **231** editorial sound-type records.
- Do not add these numbers together. A record source, content hash and sound-type are not equivalent entities.

## Actual deliverables
1. Build a PRIVATE SQLite FTS5 metadata index in `internal/ai-metadata-index/v1/versions/`, write a versioned manifest to `internal/ai-metadata-index/v1/current.json` after R2 HEAD and checksum verification.
2. Normalize source/provider, taxonomy hints, animal species, habitat, region, record duration, licence, original attribution and R2 asset presence. Keep unknown acoustic properties unknown; do not infer sound from filenames.
3. Validate full source populations and run sample queries (rainforest birds, forest stream, winter wind, frogs/crickets, soft piano).
4. Provide a **read-only authenticated, low-latency query interface** before claiming the user can search metadata immediately. A private R2 SQLite file alone does not provide ChatGPT with direct query access. Prefer an authenticated Cloudflare Worker + D1 FTS5 interface if Cloudflare deployment permissions are available, or another identity-controlled query gateway that can be invoked by ChatGPT. Never expose full private source inventories, private R2 asset URLs or credentials on public GitHub Pages or public Actions logs.
5. Add query-by-soundscape and intent expansion, filtered search by duration, licence, `has_r2_audio`, habitat, species, and coverage gaps. Use FTS lexical search as baseline; improve semantic ranking only when embeddings/acoustic features are actually available and verified.
6. Record top-N result trace and source attribution; candidate search does not confer rights to publish on YouTube.
7. Keep older WS2 and WS3 automated bulk audio ingestion disabled; never silently change production Studio, main, or access controls. No audio bulk downloads.

## Important limitation
The initial Python index builder writes a private R2 SQLite FTS5 index, **not** a publicly callable search API. Background automation must continue implementing a secure query gateway and verifying actual ChatGPT retrieval. Report index ready and AI-access ready as **two separate states**.

## Current pilot run
- GitHub feature branch: `feature/ai-metadata-search-index-20261113`.
- CI: `.github/workflows/build_private_ai_metadata_index_20261113.yml`.
- Script: `scripts/build_private_ai_metadata_index.py`.
- First run: [GitHub Actions #43413227081](https://github.com/WhiteNoiseChoir/whitenoisechoir.github.io/actions/runs/43413227081).
- No automated export to Studio without explicit user request.

## Acceptance criteria
- Stored record counts and checksum validated on R2.
- AI query auth is enforced, access possible from a ChatGPT-supported connector or authenticated integration.
- 5 sample soundscape prompts return accurate, grounded records with provenance and statuses; private data is not public.
- Document query latency and status/error handling; don't label index as instant until measured.

## Verified results — 2026-11-13 18:09 Vietnam time (11:09 UTC)
- [Build run #43413227081](https://github.com/WhiteNoiseChoir/whitenoisechoir.github.io/actions/runs/43413227081) **SUCCESS**.
- R2 private SQLite FTS5 index: `internal/ai-metadata-index/v1/versions/20261113T110930Z-7f5379d40ea8f9b6.sqlite` (13,828,096 bytes), manifest `internal/ai-metadata-index/v1/current.json`.
- **22,239 unique indexed IDs** = 19,680 unique nature SHA-256 IDs + 2,559 music candidate IDs. 19,935 source JSON records include 255 duplicate nature audio IDs; this is **not** a distinct species count.
- Source metadata and canonical audio metadata overlap; 20,607 canonical audio records were not independently merged into this version.
- Five smoke queries returned 8 hits each, but ranking is imperfect: e.g. `winter snow wind` prioritizes music candidates without audio, and `frog crickets night` returns generic music night. Do not treat these as validated multi-layer matches; next ranking step must enforce individual sound roles, `has_r2_audio`, and class filters.
- Private index ready: **YES**. Authenticated GPT-accessible search gateway deployed and tested: **NO**.

## Secure D1 gateway implementation (staging, not deployed)
- `internal/metadata-ai-search/worker.mjs`: Cloudflare Worker endpoint `GET /search` with JWT verification against Cloudflare Access issuer/JWKS and configured application AUD, bounded top-N results, D1 prepared statements, optional `class`, `has_audio`, `region`, `license`, `min_duration`, `max_duration` filters. No public fallback.
- `scripts/export_private_metadata_d1.py`: checksum-verifies private R2 SQLite, creates ordered D1 SQL import batches in private R2 under `internal/ai-metadata-index/v1/d1-staging/`. Do not publish SQL files.
- Required deployment (not yet completed): provision private D1 database, import staged SQL batches in order, bind `METADATA_DB`, configure `ACCESS_TEAM_DOMAIN` and `ACCESS_AUD`, enforce Cloudflare Access route policy, deploy Worker with authenticated domain, and integrate a supported GPT connector/OAuth path. The user must not be told GPT can query until real authenticated queries succeed.
- Never copy private metadata to GitHub Actions artifacts or logs; all metadata files remain R2-private.
