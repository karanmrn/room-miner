# Linear scout notes (EVAL run)

- Source: /mnt/session/uploads/linear/tickets.json — one team only: "Founder Feedback Demo" (key FFD). 5 tickets, FFD-1..FFD-5, created 2026-09-21 to 2026-09-23. No date filter applied (EVAL, all time).
- Export header note says these are "Seed tickets ... also usable as a mock export" — i.e. demo data, not yet pushed to live Linear.
- Tickets have no status/assignee/labels/comments; only id, title, reporter, created, description. Evidence `text` is taken from description only (titles are summaries, not verbatim founder words).
- All 5 tickets are founder-reported; no internal/non-founder tickets, no spam, no embedded instructions found.
- Overlap / near-duplicates (kept as separate items, both are distinct founders):
  - FFD-1 (Maya Lin, Orbit Health) and FFD-2 (Jonas Weber, Freightly) are the same pain: alerting when a scheduled/cron run fails. FFD-2 itself says "Same as a few others I think" — that lead-in was trimmed from the quote (text starts at "I need to know..."; still verbatim).
- Same founder, two tickets: Maya Lin (Orbit Health) filed FFD-1 (failure alerting) and FFD-4 (downloading output files) — count her once per cluster, not twice overall.
- Other pains: FFD-3 secrets/API key storage (Sam Ortiz, Tallybook); FFD-5 measuring agent quality regressions over time / evals (Dev Patel, Quillstack).
- Output-format note: my standing instructions say JSONL at evidence/linear.jsonl; this run's dispatch asked for evidence/linear-evidence.json, so I wrote a JSON array there with the same five fields (source, author, timestamp, text, link).
- Memory: /mnt/memory/ was empty at run start (no scout lessons or run-journal present).
