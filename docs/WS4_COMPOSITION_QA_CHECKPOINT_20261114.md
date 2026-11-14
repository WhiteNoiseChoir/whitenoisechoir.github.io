# WS4 Composition QA checkpoint — 2026-11-14

Scope: **feature branch only**, no production or R2 mutation. This checkpoint records benchmark scaffolding, **not** successful relevance testing.

## Inputs and baseline
- Baseline index: 22,239 (19,680 unique nature + 2,559 music candidates), **not** the same as audio files verified for playback.
- WS1 contract QA uses mocked D1; do not count as live retrieval.
- WS2 enriched metadata is incomplete; many habitat values are missing.
- WS3 candidates are not yet YouTube-rights-verified.
- No verified live D1 search results or R2 private SQLite search output were available in this run.

## Delivered
- 30 editorial benchmark cases covering Sleep and Relaxation, habitat, event/texture/bed roles and distance/time language.
- Offline evaluator accepts real top-N results as JSON, outputs per-case taxonomy relevance proxy, verified R2 flag rate, license presence, duplicates, and failures.
- The evaluator **does not** claim audio decode, loudness, sonic suitability, actual copyright clearance or true human-graded relevance.

## Next execution
1. Obtain actual top-5 retrieval results for each case from private offline FTS5 or authenticated Worker, without publishing private metadata.
2. Run `python scripts/ws4_composition_qa.py --results /secure/results.json --output /secure/ws4_report.json`.
3. Human-grade relevance and compare ranker A/B, add negative filters for distraction and taxon/habitat.
4. Run repeatable regression tests, then set owner-approved thresholds before stopping WS4.

No score is reported until real retrieval outputs exist. No audio downloaded or published.
