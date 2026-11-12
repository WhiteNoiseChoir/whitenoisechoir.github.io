# Coverage-first multi-source discovery (11 Nov 2026)

## Goal
Maximize **distinct target metadata coverage** across the 1,816 SND-TAX identifiers, especially legacy-uncovered P0 targets. Total file count is **not** the success metric.

## Architecture
- `scripts/coverage_first_multisource.py` searches **Openverse**, **Wikimedia Commons**, and **Internet Archive** using public metadata endpoints.
- **Freesound APIv2** and **Xeno-canto APIv3** adapters are optional, activated only by `FREESOUND_API_KEY` or `XENO_CANTO_API_KEY` secrets respectively. Their access/usage terms must be checked before activating for commercial purposes.
- Source-independent lexical normalization and cautious evidence matching are used to nominate up to three candidates per target, favoring distinct providers.
- Only explicit CC0/CC BY signals are accepted; the absence of usable rights metadata excludes a candidate. A recording is **not verified** merely because an item title or species name matches.
- No media bytes are downloaded. Internet Archive matches are item-level and require later per-file verification. Openverse can overlap other providers.
- The workflow runs four sequential chunks and persists progress after every five codes.
- It reads the encrypted catalog target bundle and legacy coverage counters in Cloudflare R2 but writes only the independent encrypted `internal/wnc-catalog-20261111/coverage-first-v1.enc` state. Never modify the legacy ingest queue or production `main` to advance this stage.
- `COVERAGE_DISCOVERY` and `COVERAGE_CHECKPOINT` log lines summarize progress without exposing sensitive catalog metadata or credentials.

## Reporting metrics
1. Number and percentage of target codes with one or more new **metadata candidates** (distinct from verified audio).
2. Previously mapped codes and missing P0 codes.
3. Candidates by source and provider errors.
4. Query cursor and retry-queue completion.
5. File downloads (always zero in this discovery stage).

## Guardrails
- Respect API rate limits and `Retry-After`, avoid bulk downloading, record errors separately, do not invent license clearance.
- A successfully completed workflow segment does not imply all 1,816 identifiers are covered.
- Entries are preliminary. Before publishing or downloading, individually verify availability, exact recording contents, rights, attribution, and duplicates.
- Use GitHub Actions log evidence to evaluate provider yields before broadening queries or increasing load.
