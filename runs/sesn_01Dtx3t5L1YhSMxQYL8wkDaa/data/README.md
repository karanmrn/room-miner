# Room Miner data: LIVE-ROUTED run `live-routed-karan-2026-09-23`

Built by the data analyst. It uses Python 3 and the standard library only. Rebuild with:

```
python3 data/build.py && python3 data/render.py
```

`build.py` writes `room.db` and `metrics.json`. `render.py` writes `../dashboard.html` from `metrics.json` only.
Set `ROOM_OUT=/some/copy` to run both scripts against a copy. A negative test used a mutated copy in /tmp/fake: a report founder count, a tally row, a quote, a removed Notion row, a removed brief and a fake thread. Every one of those mutations tripped a check.

## Sources

| Source | Format | Fields | Rows | Quality problems |
|---|---|---|---|---|
| `evidence/call.jsonl` (miner) | JSONL | source, author, timestamp, text, link | 4 (karan Q2–Q5) | No `id` field. `timestamp` is null in all 4 rows. Q3 and Q5 each map to 2 clusters. Q5 opens with "All three:", but the recorded question lists no options. |
| `evidence/call-context.jsonl` (miner) | JSONL | same 5 | 3 (karan Q1, Q6, Q7) | No `id`. `timestamp` null. These are context answers (use case, definition of done, closing). Q6 supports 2 clusters. |
| `evidence/linear.jsonl` (linear-scout) | JSONL | same 5 | 5 (FFD-1..5) | Seed/mock export with no status field, so open vs closed is unknown. FFD-2 is a trimmed excerpt. Maya Lin filed 2 tickets (FFD-1 and FFD-4), which are different pains. These are the same items counted in the 2026-09-23 EVAL run. |
| `evidence/notion.jsonl` (notion-scout) | JSONL | same 5 | 6 | Seed/mock data. `timestamp` null in all 6 rows. notion-004 is a note-taker **paraphrase** stored under Omar Haddad, and the schema has no type field. notion-005 and notion-006 are authored by "mentor notes", not a founder. Links point to /mnt/session/uploads (outside outputs). |
| `calls/karan.md` | Q/A markdown | Q:, A: | 7 Q / 7 A | Live founder call. No timestamps. |
| `briefs/karan.md` | markdown | use_case, current_workaround, blockers, definition_of_done, cma_mapping | 1 brief | Only karan has a brief in this run. The 4 earlier call founders' briefs are not in the outputs. |
| `clusters.json` (miner) | JSON | run, needs_briefs, evidence_files, clusters[] (id, name, kind, status, founders, founders_evidenced_this_run, sources, paused, primitives, quotes[], fix, rank, distinct_founders), top3_fixes[], karan_blocker_map[], unclustered[] | 13 clusters, 21 quotes + 1 context quote, 3 fixes | Carried clusters use status "carried (no evidence in this run)"; I normalised that to *unchanged*. 3 clusters have no quotes (runaway-spend, private-network-data, human-approval-gate). |
| `room-report.md` (miner) | markdown | ranked table, top-3 section, tally table | 13 ranked rows, 12 tally rows, 33 double-quoted strings | Used only for verification. All 33 quoted strings are verbatim evidence. |
| `run-manifest.json` (coordinator) | JSON | mode, founder, steps[] (step, task, delegated_to, outputs, status, notes) | 5 steps | Step 5 (data-analyst) has `outputs: []` and `in_progress`, so the expected outputs come from the dispatch. |
| `work/threads.json` (coordinator) | JSON | founder → role → thread id | 4 entries (3 agent threads + 1 human) | No thread ids recorded for the miner or the data-analyst. |
| `work/pending-triggers.json` | JSON | miner[], data-analyst[], status | 2 trigger lists | The status "deferred until CALL COMPLETE" is stale. Not used for metrics. |
| `/mnt/memory/room-miner-pain-library/*.md` | markdown | id, kind, distinct_founders, first_seen, last_seen, primitives, Founders refs, History | 13 cluster files + `_index.md` | The prompt path /mnt/memory/pain-library/ does not exist, so I used the room-miner-* store. The miner had already updated it for this run, so status comes from each file's History line for this run. It holds refs to earlier-run call transcripts (priya, tomas, aisha, ben) that are not in the outputs. |

Across all evidence: 18 items. 13 of them have no timestamp; only the Linear items are dated. There are 0 exact duplicates.
Unattributed quotes: none. There is 1 paraphrase attributed to a founder (notion-004) and 2 mentor items. None of them are quoted as founder words.

## room.db (sqlite3)

| Table | Rows | Notes |
|---|---|---|
| evidence(id, source, author, timestamp, text, link, file, item_type, cluster_status, note) | 18 | Synthesised ids: `call:karan:Qn`, `call-context:karan:Qn`, `FFD-n`, `notion-00n` (file order, which matches the library refs) |
| founders(name, company, sources, has_brief, brief_path, in_this_run, primitives, label) | 11 | sources is the cumulative set from the library plus this run |
| clusters(id, name, primitive, first_seen, last_seen, founder_count, kind, rank, status, sources, fix) | 13 | `primitive` is a comma-joined list; the normalised form is in cluster_primitives. status is new, growing or unchanged |
| cluster_evidence(cluster_id, evidence_id) | 15 | Mapped from clusters.json quotes, then cross-checked against pain-library refs (identical) |
| cluster_founders, cluster_primitives, founder_primitives | 20 / 28 / 32 | founder_primitives is the founder-level attribution from `_index.md` |
| library_refs(cluster_id, founder, source, ref, evidence_id, in_this_run) | 32 | Library evidence refs. `in_this_run=0` for earlier-call refs not in outputs |
| quotes(cluster_id, evidence_id, author, source, link, quote, verbatim, role) | 22 | 21 quotes + 1 context quote, all verbatim |
| top3_fixes | 3 | From clusters.json |
| agent_checks, agent_claims, threads | 11 / 12 / 4 | The per-agent "did its job" check |

## metrics.json keys

`headline`, `founder_definition_of_done`, `top3_fixes`, `top_clusters_by_founders`, `pains_by_primitive`, `pains_by_source`, `evidence_items_per_source`, `evidence_items_per_file`, `founders_per_cluster`, `cluster_status_vs_last_run`, `coverage`, `agent_check`, `cost` (display "not available" plus `spec`, which defines the per-thread token/$ metric to capture from the session event stream), `data_quality`, `verification` (194 checks), `room_db_tables`.

## Method notes

- **Primitive tally** is founder-level: a founder counts for a primitive only where their own evidence implicates it, using the `_index.md` attribution. This is the same method as the report. `founders_if_counted_per_cluster` is also kept, to show how cluster-level counting would inflate the numbers (e.g. multiagent would go from 2 to 5).
- **Per-agent check**: for every manifest step, each expected output must exist and be non-empty, *and* each numeric claim in the step notes must match the files: question count, item counts, cluster/requirement/founder counts, new clusters, run-opacity growth, verbatim quotes, and presence of the top-3 section. The data-analyst's own step is reported as a self-check and not counted. **Stray threads** are the agent thread ids in threads.json that no manifest step references.
- **Cost** is never estimated. Every cost cell is "not available" until per-thread usage telemetry exists; see `metrics.cost.spec`.
