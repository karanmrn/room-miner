# Room report: where founders get stuck building managed agents (LIVE-ROUTED, karan, 2026-09-23)

**Inputs this run:** 1 live founder call (karan: calls/karan.md, briefs/karan.md), evidence/linear.jsonl (5 seed/mock FFD tickets), evidence/notion.jsonl (6 items from 1 seed/mock page). I converted karan's problem answers into evidence/call.jsonl (Q2–Q5). His use case, definition of done and closing answer (Q1, Q6, Q7) are in evidence/call-context.jsonl so that any quote from them can be checked.

**How counting works:** Founder counts are cumulative, matched against the pain library (/mnt/memory/room-miner-pain-library/). karan is the one new founder, which makes **11 distinct founders** in total. The Linear and Notion items are the same seed items counted in the 2026-09-23 EVAL run, so those founders are not counted again. The earlier call founders (Priya, Tomas, Aisha, Ben) are counted from the library, but their transcripts are not in this run's inputs, so **none of their words are quoted here**. Every quote below exists character for character in an evidence file; a script checked all of them.

**Change since last run:** 1 cluster grew (run-opacity, 2 → 3, karan). 3 clusters are new, all from karan: multiagent-misrouting, unverified-completion and context-rot-task-drift. 9 clusters are unchanged.

---

## Top 3 fixes (karan's Monday list)

The fixes are ranked by the number of distinct founders each one would unblock.

### 1. Per-thread trace and cost in the session event stream (API change): 3 founders (Tomas, Ben, karan)
Tag every session event with `thread_id` and agent name. Keep a running token and cost total per thread in the event stream. Add a per-thread summary call that returns the last step, the wait state and the cost. Finding out which agent did what, and at what cost, then becomes one API call instead of a trace dig, and a wasted thread shows up with its price attached.
- "I lost time digging through the trace to find out what happened" [call] (calls/karan.md#Q5)
- "it cost money on a wasted thread." [call] (calls/karan.md#Q5)
- "a check that proves each agent did its job and what it cost" [call] (calls/karan.md#Q6)

### 2. Failure webhooks for deployments, plus an idle timeout for sub-threads (API change): 3 founders (Maya, Jonas, Tomas)
Add webhook events for session failed, errored and terminated. Give multiagent sub-threads a default idle timeout that raises `thread.idle_timeout` to the coordinator and fires the same webhook. Ship it with a doc recipe, *Get pinged when a scheduled run fails*.
- "Our scheduled agent errored at 2am. We only found out when the team asked where the report was." [linear] (FFD-1)
- "I need to know when the cron run breaks. Right now I check the console by hand every morning." [linear] (FFD-2)

### 3. Persisted outcome verdicts per session and per sub-agent thread (API change): 3 founders (Dev, Omar, karan)
Each session, and each multiagent thread, gets a stored verdict record: criteria met yes/no, grader rationale, agent version and cost. Add a list/aggregate endpoint grouped by agent version. This one record is both karan's "check that proves each agent did its job" and Dev's and Omar's quality scoreboard over time. It covers two clusters: unverified-completion and no-quality-scoreboard.
- "I stopped trusting the result because I couldn't tell if the task was really done" [call] (calls/karan.md#Q5)
- "We changed the instructions last week and I have a feeling the output got worse, but I can't prove it." [linear] (FFD-5)
- "I have no scoreboard. I tweak something, eyeball two outputs, and hope." [notion] (/mnt/session/uploads/notion/office-hours-notes.md#Session with Omar Haddad (Stackly))

The next fix in line is run context for recurring deployments (stale-recurring-runs, 2 founders).

---

## karan's blockers mapped to clusters

Source: briefs/karan.md and calls/karan.md.

| karan's blocker | Cluster | Evidence |
|---|---|---|
| Context rot / memory gets botched | **context-rot-task-drift** (new) | calls/karan.md#Q3 |
| Wrong-agent routing, placeholder sent to the wrong thread | **multiagent-misrouting** (new) | calls/karan.md#Q3, #Q4 |
| Can't tell if the task was really done | **unverified-completion** (new); fixed by Top fix 3 | calls/karan.md#Q5 |
| Digging through the trace | **run-opacity** (grew); fixed by Top fix 1 | calls/karan.md#Q5 |
| Cost of wasted threads | **run-opacity** (grew; per-thread cost); fixed by Top fix 1. Prevention is in multiagent-misrouting. | calls/karan.md#Q5 |
| Reads transcripts by hand, forgets to fix (status quo) | No CMA cluster. This is the job his agent replaces; the brief maps it to a Monday **deployment** with an **outcome**. | calls/karan.md#Q2 |

karan counts once in each of four clusters, and never twice in the same cluster.

---

## Clusters ranked by distinct founders

Ties are broken by, in order: number of source types, paused or stopped builds, founders evidenced in this run's inputs, and new clusters first.

| # | Cluster | Founders | Status | Sources | Primitives |
|---|---|---|---|---|---|
| 1 | silent-run-failures | 3 | unchanged | linear, call | webhooks, deployment, session, multiagent |
| 2 | run-opacity | 3 | **grew (+karan)** | call | session, multiagent, budget |
| 3 | stale-recurring-runs | 2 | unchanged | call, notion | deployment, memory store |
| 4 | no-quality-scoreboard | 2 | unchanged | linear, notion | outcome, agent |
| 5 | secrets-in-prompt | 2 | unchanged | call, linear | vault, MCP connector |
| 6 | runaway-spend | 1 | unchanged (library only) | call | budget, outcome |
| 7 | private-network-data | 1 | unchanged (library only) | call | MCP connector, environment, vault |
| 8 | multiagent-misrouting | 1 | **new** | call | multiagent |
| 9 | unverified-completion | 1 | **new** | call | outcome, multiagent, session |
| 10 | context-rot-task-drift | 1 | **new** | call | session, memory store |
| 11 | session-file-retrieval | 1 | unchanged | linear | files API |
| 12 | sandbox-dependencies | 1 | unchanged | notion | environment |
| — | human-approval-gate (requirement, not a blocker) | 1 | unchanged (library only) | call | permission policy, files API |

### 1. silent-run-failures: failed or stalled runs fail silently, and nobody is told (3 founders: Maya Lin, Jonas Weber, Tomas)
When an unattended run errors or a sub-agent hangs, nothing signals the failure. Tomas paused his build over it.
- "Our scheduled agent errored at 2am. We only found out when the team asked where the report was." [linear] (FFD-1)
- "I need to know when the cron run breaks. Right now I check the console by hand every morning." [linear] (FFD-2)
- **Primitives:** webhooks, deployment, session, multiagent
- **Fix (API change):** see Top fix 2.

### 2. run-opacity: can't reconstruct what a run did, which agent did it, or what it cost (3 founders: Tomas, Ben, karan). Grew.
After a bad run, founders piece the story together by hand from raw traces or bills, with no per-agent steps and no per-thread cost. karan joins this cluster.
- "I lost time digging through the trace to find out what happened" [call] (calls/karan.md#Q5)
- "it cost money on a wasted thread." [call] (calls/karan.md#Q5)
- "a check that proves each agent did its job and what it cost" [call] (calls/karan.md#Q6)
- **Primitives:** session, multiagent, budget
- **Fix (API change):** see Top fix 1.

### 3. stale-recurring-runs: recurring runs repeat stale work (2 founders: Priya, Lena Hoffmann)
Scheduled runs don't know what changed since the last run, or what earlier runs already handled. Priya paused her build.
- "It doesn't remember which carriers we already escalated" [notion] (/mnt/session/uploads/notion/office-hours-notes.md#Session with Lena Hoffmann (Parcelwise))
- "so it re-flags them every day" [notion] (/mnt/session/uploads/notion/office-hours-notes.md#Session with Lena Hoffmann (Parcelwise))
- Priya's evidence is from the 2026-09-23 calls and is not in this run's inputs.
- **Primitives:** deployment, memory store
- **Fix (API change):** deployments inject run context (`scheduled_for`, `run_number`, `last_successful_run_at`) into every session they start. A *Designing a recurring agent* guide keeps per-run inputs separate from what is stored in the memory store.

### 4. no-quality-scoreboard: no way to score agent quality over time or across changes (2 founders: Dev Patel, Omar Haddad)
- "We changed the instructions last week and I have a feeling the output got worse, but I can't prove it." [linear] (FFD-5)
- "I have no scoreboard. I tweak something, eyeball two outputs, and hope." [notion] (/mnt/session/uploads/notion/office-hours-notes.md#Session with Omar Haddad (Stackly))
- The note-taker's paraphrase in Omar's section (investors, no numbers) is context only. It is not quoted.
- **Primitives:** outcome, agent
- **Fix (API change):** see Top fix 3 (persisted outcome verdicts keyed by agent version, with an aggregate endpoint).

### 5. secrets-in-prompt: no obvious place for API keys, so they end up in the prompt (2 founders: Priya, Sam Ortiz)
- "I don't want the key in the prompt." [linear] (FFD-3)
- "What's the right place to put it so the agent can use it but can't leak it?" [linear] (FFD-3)
- Priya's evidence is from the 2026-09-23 calls and is not in this run's inputs.
- **Primitives:** vault, MCP connector
- **Fix (doc):** a *Where do API keys go?* vault quickstart: store the key in a vault and reference it from the MCP connector or tool config. Link it from the agent-creation page, and have the API return a warning when a key-shaped string appears in a system prompt.

### 6. runaway-spend: a runaway run with no spend cap or stopping point (1 founder: Ben). Carried from the library.
Nothing in this run's inputs covers this cluster, so there are no quotes; Ben's transcript is not in the inputs. Ben turned his agent off.
- **Primitives:** budget, outcome
- **Fix (API change):** a per-session budget cap, on by default for scheduled deployments, with a webhook at 80% and at the cap.

### 7. private-network-data: the agent can't reach data inside the company's VPC (1 founder: Aisha). Carried from the library.
Nothing in this run's inputs covers this cluster, so there are no quotes. Aisha paused her build.
- **Primitives:** MCP connector, environment, vault
- **Fix (doc + reference skill):** *Reach a database inside your VPC*, built around a self-hosted MCP server that only makes outbound connections and exposes a narrow read-only tool.

### 8. multiagent-misrouting: the coordinator hands work, or a placeholder, to the wrong sub-agent (1 founder: karan). New.
- "sometimes calling the wrong agent for the task" [call] (calls/karan.md#Q3)
- "It sent a placeholder to the wrong agent thread" [call] (calls/karan.md#Q4)
- **Primitives:** multiagent
- **Fix (API change):** validate handoffs on multiagent sends. Each callable agent declares a role and an input contract. If a send's payload is empty, is a known placeholder, or fails the target's contract, it is rejected back to the coordinator along with the list of agents and their roles, instead of starting a wasted thread.
- Internal corroboration (not counted, not evidence): the 2026-09-23 room-miner run journal records the same failure in this pipeline. The coordinator spawned a stray sub-agent whose whole task text was a placeholder.

### 9. unverified-completion: can't tell whether each agent actually finished its job (1 founder: karan). New.
- "I stopped trusting the result because I couldn't tell if the task was really done" [call] (calls/karan.md#Q5)
- "a check that proves each agent did its job" [call] (calls/karan.md#Q6)
- **Primitives:** outcome, multiagent, session
- **Fix (API change):** per-thread outcome verdicts (see Top fix 3).
- Related clusters: no-quality-scoreboard (quality over time) and silent-run-failures (no failure signal). I kept this cluster separate because karan's pain is the missing *success* proof for each sub-agent on each run.

### 10. context-rot-task-drift: the agent loses track of the task mid-run (1 founder: karan). New.
- "the agent loses track of what it needs to be done" [call] (calls/karan.md#Q3)
- "often context rot and memory gets botched" [call] (calls/karan.md#Q3)
- **Primitives:** session, memory store
- **Fix (skill + guide):** a *task ledger* skill. At the start of a run it writes the plan and checklist to a memory store, then re-reads and updates them before each step and after any context compaction. A guide, *Keeping long-running agents on task*, goes with it.
- Related cluster: the memory half of stale-recurring-runs. I kept them apart because karan describes drift *within* a run, while Lena describes forgetting *across* runs. This is a judgement call to revisit if more founders say "memory".

### 11. session-file-retrieval: can't get output files out of a finished session (1 founder: Maya Lin)
- "The agent says it wrote report.pdf to outputs, but I can't work out how to download it after the session." [linear] (FFD-4)
- "The docs mention a scope thing I don't get." [linear] (FFD-4)
- **Primitives:** files API
- **Fix (doc):** an end-to-end *Get files out of a session* example that explains file scope in plain language.

### 12. sandbox-dependencies: setting up sandbox dependencies eats the first day (1 founder: Lena Hoffmann)
- "Half my first day was fighting pip." [notion] (/mnt/session/uploads/notion/office-hours-notes.md#Session with Lena Hoffmann (Parcelwise))
- "The sandbox didn't have pandas and the install kept timing out." [notion] (/mnt/session/uploads/notion/office-hours-notes.md#Session with Lena Hoffmann (Parcelwise))
- **Primitives:** environment
- **Fix (API change):** environments declare packages, which are installed once at build time and cached across sessions. Preinstall pandas and numpy.

### Requirement: human-approval-gate, a human must approve before the agent acts externally (1 founder: Aisha). Carried from the library.
This is a requirement, not a blocker, and is excluded from the tally. There is no founder quote in this run. Mentor context from this run (not a founder quote, not counted): "Recurring theme: people want the agent to act, but only after a human says yes." [notion] (/mnt/session/uploads/notion/office-hours-notes.md#Mentor takeaways)
- **Fix (doc + skill):** a *Draft, then approve* pattern.

---

## Evidence not clustered, and data notes
- **calls/karan.md#Q2** (status quo: manual reading of transcripts, then forgetting to fix) is the job-to-be-done, not a CMA blocker.
- **Mentor note on scheduling / the manual run endpoint** (office-hours-notes.md#Mentor takeaways) is uncounted, as in the last run.
- **Omar's note-taker paraphrase** is context for no-quality-scoreboard and is not quoted.
- **Transcript quirk:** karan's Q5 answer starts "All three:", which suggests the interviewer offered three options, but the recorded question lists none. That is worth checking in discovery method: the question may have been leading, or the transcript may be incomplete.
- **Seed data:** the Linear and Notion items are seed/mock data. The Linear export has no status field, so it can't show which tickets are still open. Calls and Notion items have no timestamps.
- **Evidence without instructions:** no evidence text contained instructions.

---

## Blocker tally by CMA primitive

This covers blocker clusters only; the human-approval-gate requirement is excluded. A primitive is attributed to a founder only where that founder's own evidence implicates it. Attributions for the earlier founders are rebuilt from the pain library notes and match the last run's totals (deployment 4, session 4, multiagent 1).

| Primitive | Distinct founders blocked | Founders | Evidenced in this run | Change vs 2026-09-23 | Blocker clusters |
|---|---|---|---|---|---|
| session | 5 | Maya, Jonas, Tomas, Ben, karan | Maya, Jonas, karan | +1 (karan) | silent-run-failures, run-opacity, unverified-completion, context-rot-task-drift |
| deployment | 4 | Maya, Jonas, Priya, Lena | Maya, Jonas, Lena | 0 | silent-run-failures, stale-recurring-runs |
| outcome | 4 | Ben, Dev, Omar, karan | Dev, Omar, karan | +1 (karan) | runaway-spend, no-quality-scoreboard, unverified-completion |
| vault | 3 | Priya, Sam, Aisha | Sam | 0 | secrets-in-prompt, private-network-data |
| MCP connector | 3 | Priya, Sam, Aisha | Sam | 0 | secrets-in-prompt, private-network-data |
| multiagent | 2 | Tomas, karan | karan | +1 (karan) | silent-run-failures, run-opacity, multiagent-misrouting, unverified-completion |
| budget | 2 | Ben, karan | karan | +1 (karan) | run-opacity, runaway-spend |
| memory store | 2 | Lena, karan | Lena, karan | +1 (karan) | stale-recurring-runs, context-rot-task-drift |
| webhooks | 2 | Maya, Jonas | Maya, Jonas | 0 | silent-run-failures |
| environment | 2 | Lena, Aisha | Lena | 0 | sandbox-dependencies, private-network-data |
| agent | 2 | Dev, Omar | Dev, Omar | 0 | no-quality-scoreboard |
| files API | 1 | Maya | Maya | 0 | session-file-retrieval |
