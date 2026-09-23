# Room Miner: definition of done

1. `/mnt/session/outputs/room-report.md` ranks at least 5 pain clusters by the number of distinct founders mentioning each.
2. Every cluster has at least 2 verbatim quotes, each tagged with its source (`call`, `linear` or `notion`) and a link or transcript reference.
3. Every quoted string appears character for character in an evidence item under `/mnt/session/outputs/evidence/`; no paraphrase is presented as a quote.
4. Evidence from all three sources (`call`, `linear`, `notion`) appears in the report.
5. Every founder called has a needs brief in `/mnt/session/outputs/briefs/` with all 5 fields (use_case, current_workaround, blockers, definition_of_done, cma_mapping), and `cma_mapping` uses real CMA primitive names.
6. Every cluster ends with one concrete fix (a doc, skill or API change), and the report ends with a blocker tally table by CMA primitive.
7. `/mnt/session/outputs/run-manifest.json` has one entry for every numbered step in the task, each marked `done` with outputs that exist; `dashboard.html` and `data/metrics.json` exist and every number on the dashboard appears in `metrics.json`.
