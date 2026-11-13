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
