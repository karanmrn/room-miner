# Room Miner data layer: run eval-2026-09-23 (EVAL, rebuilt after the miner revised its output)

Built by the data analyst from the miner's output. Python 3 standard library only.
Rebuild with `python3 data/build.py && python3 data/render.py`. `build.py` writes `room.db` and `metrics.json`. `render.py` writes `../dashboard.html` from `metrics.json` only.

## Sources read (none were modified)

| Source | Format | Fields | Rows | Quality notes |
|---|---|---|---|---|
| `evidence/call.jsonl` (written by miner) | JSONL | source, author, timestamp, text, link | 17 | No `id` field, so the DB id is `call:<slug>:Q<n>` built from the link. All 17 texts equal the full answer line in `calls/<slug>/transcript.md`. `timestamp` is null on all 17 (the calls are undated). 3 items are not linked to any cluster: aisha Q5, aisha Q6, ben Q6. Aisha Q5 is an explicit non-problem but sits here, not in the non-problems file. |
| `evidence/call-nonproblems.jsonl` (miner) | JSONL | same 5 fields | 1 | Tomas Q5 only. Timestamp is null. |
| `evidence/linear-evidence.json` (linear-scout) | JSON array | source, author, timestamp, text, link | 5 | No `id` field, so the link (FFD-n) is used as the id. All 5 match `uploads/linear/tickets.json` (reporter, created, description). FFD-2's text is a verbatim excerpt: the lead-in "Same as a few others I think:" was trimmed. Seed/mock export. Maya Lin filed 2 tickets (FFD-1, FFD-4), which land in different clusters. No duplicates. |
| `evidence/notion-evidence.json` (notion-scout) | JSON object, `items[]` | id, source, author, timestamp, text, evidence_type, context, link | 6 | 3 founder_quote, 1 note_taker_paraphrase (notion-004), 2 mentor_observation (notion-005, notion-006). Timestamp is null on all 6 (the page has no dates). Founder quotes keep their surrounding quotation marks. All 6 texts are found on the uploaded page. Seed/mock content. |
| `evidence/linear-notes.md`, `evidence/notion-notes.md` | Markdown | scout notes | n/a | Used only for context on source quirks. |
| `calls/<slug>/transcript.md` ×4 (copies at `calls/<slug>.md`) | Markdown Q/A | 8 Q/A pairs each | 32 answers | Used to verify call evidence verbatim. All 4 copies at `calls/<slug>.md` are byte-identical to `calls/<slug>/transcript.md`. Evidence links still use `calls/<slug>/transcript.md#Q<n>`. Ben's header has no company name. The "(climate-investor newsletter)" label is a descriptor added downstream. |
| `briefs/<slug>.md` ×4 (priya, tomas, aisha, ben) | Markdown | use_case, current_workaround, blockers, definition_of_done, cma_mapping | 4 | The standard location, taken from the clusters.json `needs_briefs` map. It sets `founders.has_brief` and `founders.brief_path`. All 4 are byte-identical to the legacy copies at `calls/<slug>/needs-brief.md`. This is analysis: nothing from the briefs is quoted or counted. |
| `clusters.json` (miner, revised) | JSON | needs_briefs{slug: path}, clusters[rank, id, name, kind, pain, founder_count, founders, stopped, sources, primitives, fix_type, fix, evidence_links, evidence_date_range, paraphrase_note, uncounted_support, primitive_founders, quotes[]], primitive_tally, uncounted_evidence, explicit_non_problems | 10 clusters, 30 quotes, 14 tally rows | Primary source for cluster membership, quotes and fixes. |
| `room-report.md` (miner, revised) | Markdown | ranked table, per-cluster sections, primitive tally (now the last section, at line 316) | 10 clusters, 33 block quotes, 14 tally rows | Cross-checked against clusters.json and the evidence. See Verification. |
| `/mnt/memory/room-miner-pain-library/*.md` | Markdown, one file per cluster + `_index.md` | id, kind, distinct_founders, first_seen, last_seen, primitives, Founders links, History | 10 + index | Every file was created in this run. The miner's journal says the library was empty at the start, so all clusters are "new". Not present: `digest.md`, `/mnt/memory/pain-library/`. The real pain-library path is `/mnt/memory/room-miner-pain-library/`. |

## room.db tables

| Table | Rows | Notes |
|---|---|---|
| evidence(id, source, author, timestamp, text, link, evidence_type, founder_words, file) | 29 | 18 call + 5 linear + 6 notion. `founder_words=0` for notion-004/005/006 and the call non-problem. |
| founders(founder_key, name, company, sources, has_brief, brief_path, stopped_or_paused) | 10 | Distinct authors of founder-worded evidence. "mentor notes" is not a founder. `brief_path` = `briefs/<slug>.md` for the 4 call founders, NULL for the other 6. |
| clusters(id, rank, name, kind, pain, primitive, first_seen, last_seen, founder_count, stopped_count, sources, fix_type, fix, status_vs_last_run, paraphrase_note, uncounted_support) | 10 | `primitive` is a comma-joined list. The normalised form is in cluster_primitives. first_seen/last_seen come from the pain library. |
| cluster_evidence(cluster_id, evidence_id, role, counts_toward_founders) | 27 | 25 links from clusters.json `evidence_links` (role quoted or linked), plus 2 `context_uncounted` (notion-004, notion-006). |
| cluster_founders(cluster_id, founder_key, stopped_or_paused) | 16 | |
| cluster_primitives(cluster_id, primitive) | 22 | |
| primitive_founders(cluster_id, primitive, founder_key) | 33 | From clusters.json `primitive_founders`. The primitive tally is recomputed from this table. |
| quotes(id, cluster_id, evidence_id, seq, author, source, link, text, verbatim_in_evidence) | 30 | All 30 have `verbatim_in_evidence=1`. |
| non_problems(founder_key, topic, link, evidence_id) | 2 | |

## Counting rules

- A founder is counted only through evidence in their own words: call answers, Linear tickets, and Notion `founder_quote`. The mentor paraphrase (notion-004) and mentor observations (notion-005, notion-006) are stored in the DB but never counted.
- Each founder counts at most once per cluster and once per primitive.
- The primitive tally covers blocker clusters only. The requirement cluster (#10 human-approval-gate) is listed separately.

## Verification (all computed in build.py; results in metrics.json → verification)

- All 29 evidence items match their raw source (transcripts, tickets.json, the Notion page).
- File layout (`verification.file_layout`): 4/4 `briefs/<slug>.md` exist, are listed in `needs_briefs`, and are byte-identical to `calls/<slug>/needs-brief.md`. 4/4 `calls/<slug>.md` are byte-identical to `calls/<slug>/transcript.md`.
- All 30 cluster quotes in clusters.json are exact substrings of the linked evidence item, with matching author and source.
- All 33 block quotes in room-report.md are verbatim in the evidence. In all 10 clusters the report quotes equal the clusters.json quotes, in the same order and with the same attribution.
- Report ranked table (founders, stopped, sources, primitives, fix type), per-cluster founder headers, the 14-row primitive tally (parsed by row, so its move to the end of the file doesn't matter), the "10 distinct founders · 10 clusters" line and "Four of the ten founders stopped": all match the DB. The pain-library founder counts, primitives and evidence links also match clusters.json.
- **Mismatches found: none.**
