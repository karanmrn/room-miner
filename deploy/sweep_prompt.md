MODE: SWEEP

Update the room picture with evidence that arrived since the last run, as of this run. Do not run any discovery calls.

1. Read the latest entry in the run journal to find when the last run happened.
2. Send linear-scout to read issues in the Linear export mounted at /mnt/session/uploads/linear/tickets.json created since the last run (all of them if there is no previous run).
3. Send notion-scout to read the Notion export mounted at /mnt/session/uploads/notion/office-hours-notes.md for anything added since the last run.
4. Send the miner the new evidence, and have it update the pain-library and write /mnt/session/outputs/digest.md in SWEEP mode.
5. Send the data-analyst the miner's output, and have it rebuild data/metrics.json and /mnt/session/outputs/dashboard.html.
6. Keep /mnt/session/outputs/run-manifest.json current for every step above, and append this run's entry to the run journal.

The reader is Anthropic developer relations. Lead with what is new or growing since the last run.
