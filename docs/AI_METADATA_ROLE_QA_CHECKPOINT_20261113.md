# Metadata AI — composition retrieval QA checkpoint (2026-11-13 19:55 ICT)

## Execution
- [Private QA GitHub Actions #43429152478](https://github.com/WhiteNoiseChoir/whitenoisechoir.github.io/actions/runs/43429152478) **SUCCESS**
- Private detailed QA record: `internal/ai-metadata-index/v1/qa/composition-role-qa-20261113T125522Z.json` on R2 (not published here)
- Index: **22,239** IDs: 19,680 nature audio SHA-256, 2,559 music candidates. 19,680 entries have R2 audio keys; candidate music entries have no R2 audio.
- The 20,607 canonical audio metadata documents are a separate overlapping source and are not yet fully merged.

## Five realistic soundscape scenarios, per-layer lexical FTS search (top 30)
| Scenario | Role | FTS hits | With R2 audio in top 30 |
| --- | --- | ---: | ---: |
| Rainforest evening | rainforest birds | 30 | 30 |
| Rainforest evening | frogs | 30 | 30 |
| Rainforest evening | crickets | 30 | 30 |
| Forest stream | stream river | 30 | 30 |
| Forest stream | birds forest | 30 | 30 |
| Forest stream | wind leaves | 30 | 30 |
| Winter cabin | wind winter | 30 | 30 |
| Winter cabin | fireplace crackling | **0** | **0** |
| Winter cabin | snow | 28 | 28 |
| Tropical dawn | rainforest morning | **3** | 3 |
| Tropical dawn | birds dawn | 30 | 30 |
| Tropical dawn | waterfall | **2** | 2 |
| Soft piano | piano ambient | 30 | **0** |
| Soft piano | rain background | 30 | 23 |

## Findings and cautions
- The search is currently **OR-token lexical retrieval**, not proof of accurate sound classification or soundscape fit. Counts are candidate hits, not listening-tested matches.
- Missing fireplace/crackling role, sparse waterfall and rainforest morning are actionable gaps. Piano results are metadata-only, not playable.
- A real authenticated query gateway for ChatGPT is **not yet deployed**. The private SQLite index and staged D1 SQL do not themselves grant GPT query access.
- [D1 staging run #43420364949](https://github.com/WhiteNoiseChoir/whitenoisechoir.github.io/actions/runs/43420364949) succeeded: 558 private SQL files, 9,997,172 bytes; D1 import/Worker deployment remains outstanding.
- Do not enable WS2/WS3 or download audio in bulk. Do not publish private inventory, source rows or signed audio URLs.

## Next implementation target
1. Improve role query from broad OR to AND-first with safe fallback and grounded role score; ensure audio-required filters are applied in SQL rather than post-ranking.
2. Implement authenticated D1 Worker deployment only when credentials and Access policy are confirmed, and test 401 unauthorized plus valid JWT and five query results.
3. Merge canonical audio metadata with verified SHA identity, preserving provenance and unknowns, then rerun QA.
