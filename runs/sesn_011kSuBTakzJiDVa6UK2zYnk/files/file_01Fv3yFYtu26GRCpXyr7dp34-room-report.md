# Room report: what founders are stuck on with managed agents (EVAL)

Run: eval-2026-09-23 · Sources: 4 discovery calls (Priya, Tomas, Aisha, Ben), 5 Linear tickets (FFD-1..5), 1 Notion office-hours page (6 items) · **10 distinct founders** · 10 clusters

How to read this: clusters are grouped by underlying pain, not surface wording. They are ranked by distinct founders, then by how many founders the pain stopped or paused, then by how many source types it appears in. Every quote is copied character for character from a founder's own words in `evidence/call.jsonl`, `evidence/linear-evidence.json` or `evidence/notion-evidence.json`. Interviewer questions, needs-brief analysis (`briefs/<slug>.md`), mentor paraphrases and mentor observations are never quoted as founder words and never counted. A founder is counted at most once per cluster (Maya Lin filed FFD-1 and FFD-4, which land in different clusters).

## Ranked clusters at a glance

| # | Cluster | Founders | Stopped/paused a build | Sources | CMA primitives | Fix type |
|---|---|---|---|---|---|---|
| 1 | Failed or stalled runs fail silently: nobody gets told | 3 | 1 | call, linear | webhooks, deployment, session, multiagent | API change |
| 2 | Recurring runs repeat stale work: no per-run 'today' and no memory of earlier runs | 2 | 1 | call, notion | deployment, memory store | API change + doc |
| 3 | Can't reconstruct what a run did, which agent did it, or what it cost | 2 | 1 | call | session, multiagent, budget | API change |
| 4 | No obvious place for API keys, so they end up in the prompt | 2 | 0 | call, linear | vault, MCP connector | Doc (+ API warning hook) |
| 5 | No way to score agent quality over time or across changes | 2 | 0 | linear, notion | outcome, agent | API change + skill |
| 6 | Runaway run: no spend cap or stopping point | 1 | 1 | call | budget, outcome | API change |
| 7 | Agent can't reach data inside the company's private network (VPC) | 1 | 1 | call | MCP connector, environment, vault | Doc + reference skill |
| 8 | Can't get output files out of a finished session | 1 | 0 | linear | files API | Doc |
| 9 | Sandbox dependency setup eats the first day | 1 | 0 | notion | environment | API change |
| 10 | Must have a human approve before the agent acts externally *(requirement)* | 1 | 0 | call | permission policy, files API | Doc / skill |

## Clusters

### 1. Failed or stalled runs fail silently: nobody gets told

**Distinct founders: 3** (Maya Lin (Orbit Health); Jonas Weber (Freightly); Tomas (Patchwork)) · stopped/paused: Tomas (Patchwork)

**Pain:** When an unattended run errors or a sub-agent hangs, there is no failure signal. Founders find out from a missing report, a daily console check, or a coordinator that waits forever.

**Founder quotes:**

> Our scheduled agent errored at 2am. We only found out when the team asked where the report was.
>
> — Maya Lin (Orbit Health) · [linear] FFD-1 ([evidence/linear-evidence.json](evidence/linear-evidence.json))

> I need to know when the cron run breaks. Right now I check the console by hand every morning.
>
> — Jonas Weber (Freightly) · [linear] FFD-2 ([evidence/linear-evidence.json](evidence/linear-evidence.json))

> One of the sub-agents just went quiet and the coordinator kept waiting.
>
> — Tomas (Patchwork) · [call] [calls/tomas/transcript.md#Q3](calls/tomas/transcript.md#Q3)

> I could see the coordinator's last message go out, and after that just nothing, no error and no timeout.
>
> — Tomas (Patchwork) · [call] [calls/tomas/transcript.md#Q4](calls/tomas/transcript.md#Q4)

**CMA primitives:** webhooks, deployment, session, multiagent

**Fix (API change):** Add failure notifications to deployments: webhook events for session failed/errored/terminated, plus a default idle timeout on multiagent sub-threads that raises a thread.idle_timeout error to the coordinator and fires the same webhook, instead of waiting forever. Ship it with a short doc recipe, "Get pinged when a scheduled run fails".


### 2. Recurring runs repeat stale work: no per-run 'today' and no memory of earlier runs

**Distinct founders: 2** (Priya (Lumen Skin); Lena Hoffmann (Parcelwise)) · stopped/paused: Priya (Lumen Skin)

**Pain:** Scheduled runs don't know what changed since the last run. They either replay a frozen input (a hardcoded date) or forget what earlier runs already handled, so the same stale output comes back every day and trust erodes.

**Founder quotes:**

> It ran every night but kept checking stock for the 14th. I'd typed the date into the task and it just replayed it forever.
>
> — Priya (Lumen Skin) · [call] [calls/priya/transcript.md#Q6](calls/priya/transcript.md#Q6)

> Once I noticed, I stopped believing anything it told me and went back to checking Shopify myself at night.
>
> — Priya (Lumen Skin) · [call] [calls/priya/transcript.md#Q7](calls/priya/transcript.md#Q7)

> It doesn't remember which carriers we already escalated, so it re-flags them every day.
>
> — Lena Hoffmann (Parcelwise) · [notion] notion-002 ([evidence/notion-evidence.json](evidence/notion-evidence.json))

**CMA primitives:** deployment, memory store

**Fix (API change + doc):** Have deployments inject run context into every session they start (scheduled_for, run_number, last_successful_run_at) so task text never hardcodes a date. Document it in a "Designing a recurring agent" guide that separates per-run inputs (from run context) from persistent state (a memory store of items already handled, e.g. carriers already escalated).


### 3. Can't reconstruct what a run did, which agent did it, or what it cost

**Distinct founders: 2** (Tomas (Patchwork); Ben (climate-investor newsletter)) · stopped/paused: Tomas (Patchwork)

**Pain:** After a bad run, founders rebuild the story by hand, from interleaved raw logs or by matching output against the bill. They can't see per-agent steps or per-run cost.

**Founder quotes:**

> I had no idea which thread died or why.
>
> — Tomas (Patchwork) · [call] [calls/tomas/transcript.md#Q3](calls/tomas/transcript.md#Q3)

> What I got was one big interleaved stream with no clean way to tell which agent a line belonged to or what the coordinator thought it was waiting on.
>
> — Tomas (Patchwork) · [call] [calls/tomas/transcript.md#Q4](calls/tomas/transcript.md#Q4)

> the whole "auto-approve trivial PRs" goal is on hold until I can actually see what each agent is doing.
>
> — Tomas (Patchwork) · [call] [calls/tomas/transcript.md#Q6](calls/tomas/transcript.md#Q6)

> I only noticed when I checked my bill
>
> — Ben (climate-investor newsletter) · [call] [calls/ben/transcript.md#Q4](calls/ben/transcript.md#Q4)

> mostly by scrolling through the output it dumped into my doc that morning, which was this enormous pile of paper summaries. I matched that against the usage on my bill
>
> — Ben (climate-investor newsletter) · [call] [calls/ben/transcript.md#Q5](calls/ben/transcript.md#Q5)

**CMA primitives:** session, multiagent, budget

**Fix (API change):** Tag every session event with thread_id and agent name, and add a running cost/token total to the event stream. Support filtering by thread and a per-thread last-step and wait-state summary, so "which agent stalled, on what step, and what did this run cost" is answered by one API call rather than by reading raw logs.


### 4. No obvious place for API keys, so they end up in the prompt

**Distinct founders: 2** (Priya (Lumen Skin); Sam Ortiz (Tallybook))

**Pain:** Founders connecting a third-party API can't find where a credential should live, so they paste it into the prompt or stop to ask.

**Founder quotes:**

> I literally pasted my Shopify key into the prompt because I couldn't figure out where else it goes.
>
> — Priya (Lumen Skin) · [call] [calls/priya/transcript.md#Q3](calls/priya/transcript.md#Q3)

> I poked around looking for somewhere obvious to put it, didn't find anything that made sense to me, and I was tired.
>
> — Priya (Lumen Skin) · [call] [calls/priya/transcript.md#Q4](calls/priya/transcript.md#Q4)

> I don't want the key in the prompt. What's the right place to put it so the agent can use it but can't leak it?
>
> — Sam Ortiz (Tallybook) · [linear] FFD-3 ([evidence/linear-evidence.json](evidence/linear-evidence.json))

**CMA primitives:** vault, MCP connector

**Fix (Doc (+ API warning hook)):** Write a "Where do API keys go?" vault quickstart: store the key in a vault, reference it from the MCP connector or tool config, and never put it in the prompt. Link it from the agent-creation page, and make the agent/session create API return a warning with that link when it sees a key-shaped string in a system prompt or task.


### 5. No way to score agent quality over time or across changes

**Distinct founders: 2** (Dev Patel (Quillstack); Omar Haddad (Stackly))

**Pain:** After changing instructions, founders can't tell whether output got better or worse. They eyeball a couple of outputs and have no numbers.

**Founder quotes:**

> We changed the instructions last week and I have a feeling the output got worse, but I can't prove it.
>
> — Dev Patel (Quillstack) · [linear] FFD-5 ([evidence/linear-evidence.json](evidence/linear-evidence.json))

> Is there a standard way to score runs over time?
>
> — Dev Patel (Quillstack) · [linear] FFD-5 ([evidence/linear-evidence.json](evidence/linear-evidence.json))

> I have no scoreboard. I tweak something, eyeball two outputs, and hope.
>
> — Omar Haddad (Stackly) · [notion] notion-003 ([evidence/notion-evidence.json](evidence/notion-evidence.json))

*Note:* notion-004 is a mentor paraphrase (not founder words): Omar wants to show investors the agent is improving but has no numbers. It is context only and is not quoted or counted separately.

**CMA primitives:** outcome, agent

**Fix (API change + skill):** Persist outcome grader scores per session, keyed by agent version, with a list/aggregate endpoint (score by version over time). Ship an "eval harness" skill that replays a fixed input set against two agent versions and reports the score delta.


### 6. Runaway run: no spend cap or stopping point

**Distinct founders: 1** (Ben (climate-investor newsletter)) · stopped/paused: Ben (climate-investor newsletter)

**Pain:** A self-directed run kept going with no budget and no completion criterion, and cost more than the previous week in one go. The founder turned the agent off.

**Founder quotes:**

> One run went down a rabbit hole and cost me more than the whole previous week. I had no cap on it.
>
> — Ben (climate-investor newsletter) · [call] [calls/ben/transcript.md#Q3](calls/ben/transcript.md#Q3)

> There was nothing telling it "okay, that's enough, go write the draft," so it just kept going.
>
> — Ben (climate-investor newsletter) · [call] [calls/ben/transcript.md#Q4](calls/ben/transcript.md#Q4)

> so I shut it off pretty quick after that.
>
> — Ben (climate-investor newsletter) · [call] [calls/ben/transcript.md#Q3](calls/ben/transcript.md#Q3)

**CMA primitives:** budget, outcome

**Fix (API change):** Make a per-session budget cap the default on scheduled deployments (opt out, not opt in), with a webhook at 80% and at the cap. Document pairing it with an outcome stop criterion (e.g. "draft with 5-6 items written") so the run ends when the job is done.


### 7. Agent can't reach data inside the company's private network (VPC)

**Distinct founders: 1** (Aisha (Ledgerline)) · stopped/paused: Aisha (Ledgerline)

**Pain:** The cloud-hosted agent can't reach a database inside the VPC. Opening the database to the internet is unacceptable, and manual exports defeat the purpose.

**Founder quotes:**

> Our transaction DB sits inside our VPC. The agent runs in the cloud, so it just couldn't reach it and I gave up.
>
> — Aisha (Ledgerline) · [call] [calls/aisha/transcript.md#Q3](calls/aisha/transcript.md#Q3)

> I wasn't comfortable opening the database up to the internet just to test an idea, so it stopped there.
>
> — Aisha (Ledgerline) · [call] [calls/aisha/transcript.md#Q3](calls/aisha/transcript.md#Q3)

> a manual export every week defeats the purpose, so I stopped there.
>
> — Aisha (Ledgerline) · [call] [calls/aisha/transcript.md#Q4](calls/aisha/transcript.md#Q4)

**CMA primitives:** MCP connector, environment, vault

**Fix (Doc + reference skill):** Publish a "Reach a database inside your VPC" guide with a reference self-hosted MCP server. It runs inside the VPC, makes outbound connections only, and exposes a narrow read-only tool (e.g. fetch_flagged_transactions(week)) rather than raw SQL. DB credentials go in a vault, and the environment's network is limited to that connector.


### 8. Can't get output files out of a finished session

**Distinct founders: 1** (Maya Lin (Orbit Health))

**Pain:** The agent reports that it wrote a file to outputs, but the founder can't work out how to download it after the session ends. The docs' mention of "scope" doesn't help.

**Founder quotes:**

> The agent says it wrote report.pdf to outputs, but I can't work out how to download it after the session.
>
> — Maya Lin (Orbit Health) · [linear] FFD-4 ([evidence/linear-evidence.json](evidence/linear-evidence.json))

> The docs mention a scope thing I don't get.
>
> — Maya Lin (Orbit Health) · [linear] FFD-4 ([evidence/linear-evidence.json](evidence/linear-evidence.json))

**CMA primitives:** files API

**Fix (Doc):** Add an end-to-end "Get files out of a session" example to the files API docs: agent writes to outputs, then list the session's files, then download after the session ends. Explain file scope (session-scoped vs persisted) in plain language, with the exact call for each.


### 9. Sandbox dependency setup eats the first day

**Distinct founders: 1** (Lena Hoffmann (Parcelwise))

**Pain:** Common Python packages are missing from the sandbox, and installing them times out.

**Founder quotes:**

> Half my first day was fighting pip.
>
> — Lena Hoffmann (Parcelwise) · [notion] notion-001 ([evidence/notion-evidence.json](evidence/notion-evidence.json))

> The sandbox didn't have pandas and the install kept timing out.
>
> — Lena Hoffmann (Parcelwise) · [notion] notion-001 ([evidence/notion-evidence.json](evidence/notion-evidence.json))

**CMA primitives:** environment

**Fix (API change):** Let environments declare packages (a requirements list) that are installed once at environment build and cached across sessions, with a longer install timeout. Preinstall common data libraries (pandas, numpy) in the default image.


### 10. Must have a human approve before the agent acts externally

**Distinct founders: 1** (Aisha (Ledgerline))

**Pain:** A hard requirement, not a failure. In regulated work nothing can leave without a human reading it, and the founder must be able to explain what the agent did.

**Founder quotes:**

> Nothing goes to the regulator without me reading it. If the agent could send on its own, legal would shut it down on day one.
>
> — Aisha (Ledgerline) · [call] [calls/aisha/transcript.md#Q2](calls/aisha/transcript.md#Q2)

> anything touching our data or our regulator has to be something I can explain and stand behind.
>
> — Aisha (Ledgerline) · [call] [calls/aisha/transcript.md#Q8](calls/aisha/transcript.md#Q8)

*Not counted:* Mentor observation notion-006 (unnamed teams, not counted) says the same theme recurs across teams. Priya's definition of done also keeps the final send with her, but she did not raise it as a problem, so she is not counted.

**CMA primitives:** permission policy, files API

**Fix (Doc / skill):** Publish a "Draft, then approve" pattern doc and skill: a permission policy with no outbound-send tool (or one that requires human confirmation), the deliverable written as a draft file via the files API, and an outcome defined as "draft ready for review" rather than "sent".

## What founders said was NOT a problem

- **Multiagent architecture and handoffs (Tomas).** His multiagent pain is observability only (clusters 1 and 3), not orchestration design:

  > Most of my time has gone into the architecture, getting each agent to own a clean slice of the review and agreeing on what they hand to each other. That part I'm actually pretty happy with.
  >
  > — Tomas (Patchwork) · [call] [calls/tomas/transcript.md#Q5](calls/tomas/transcript.md#Q5) (in `evidence/call-nonproblems.jsonl`)

  Asked what else got in the way:

  > Honestly, nothing that stands out, just the usual rough edges you get building something like this.
  >
  > — Tomas (Patchwork) · [call] [calls/tomas/transcript.md#Q5](calls/tomas/transcript.md#Q5)

- **Drafting quality on real content (Aisha).** On a hand-exported sample the model's draft was good. Her blocker is data access (cluster 7), not model output:

  > It was better than I expected, honestly.
  >
  > — Aisha (Ledgerline) · [call] [calls/aisha/transcript.md#Q5](calls/aisha/transcript.md#Q5)

- **Ben's editorial "taste" / day-to-day draft quality: not evidenced either way.** He said so himself (Q8). This is an open follow-up, not a cluster.

## Cross-cutting impact (not a separate cluster)

Four of the ten founders stopped their build or put autonomy on hold. Three did so because one bad run cost them trust: Priya (cluster 2), Tomas (clusters 1 and 3) and Ben (cluster 6). Aisha was blocked before she could run it on real data (cluster 7). All four went back to doing the work by hand. The top three clusters are all about unattended runs: they fail silently, repeat stale work, or can't be reconstructed afterwards. Fixing deployment run context and failure webhooks, together with per-thread session events, covers the most founders.

## Evidence not counted toward founder totals

- notion-004 (mentor paraphrase of Omar): used only as context in cluster 5. Not quoted.
- notion-005 (mentor observation, unnamed teams): several teams asked about scheduling but none had tried the manual run endpoint. This doesn't match any founder-attributed cluster, so it isn't counted. It may be worth a follow-up question in future calls.
- notion-006 (mentor observation, unnamed teams): supports cluster 10. Not counted.

## Data notes

- `evidence/call.jsonl` was written by the miner: 17 problem-bearing founder answers (full answer text, verbatim; timestamp null). Quote links point to `calls/<slug>/transcript.md#Q<n>`. Copies of the transcripts are also at `calls/<slug>.md`. Explicit non-problems are in `evidence/call-nonproblems.jsonl`.
- Linear and Notion inputs are seed/mock exports (their headers say so). Notion has no dates. Calls are undated. Only the Linear items carry timestamps (2026-09-21..23).
- Needs briefs (the discovery agent's analysis, never quoted as founder words): `briefs/priya.md`, `briefs/tomas.md`, `briefs/aisha.md`, `briefs/ben.md`.
- Machine-readable clusters for the data-analyst: `clusters.json` (ranked clusters with quotes, founders, links, primitives, fixes and the primitive tally).

## Blocker tally by CMA primitive

Founders are attributed to a primitive only where their own evidence implicates it. For example, in cluster 1 multiagent is attributed to Tomas only, and deployment to Maya and Jonas only. A founder is counted once per primitive, even if they appear in several clusters that touch it. Only blocker clusters are counted (clusters 1–9). The human-approval requirement (cluster 10) is excluded here.

Requirement, not blocker: **permission policy** + **files API**, draft-then-approve (1 founder: Aisha; mentor notion-006 says the theme recurs across unnamed teams). **skill** was not the main fix location for any blocker. It appears only as the delivery vehicle for fixes 5, 7 and 10.

| CMA primitive | Distinct founders blocked | Founders whose build it stopped/paused | Clusters (#) |
|---|---|---|---|
| deployment | 4 | 1 | 1, 2 |
| session | 4 | 1 | 1, 3 |
| MCP connector | 3 | 1 | 4, 7 |
| outcome | 3 | 1 | 5, 6 |
| vault | 3 | 1 | 4, 7 |
| webhooks | 3 | 1 | 1 |
| environment | 2 | 1 | 7, 9 |
| agent | 2 | 0 | 5 |
| budget | 1 | 1 | 3, 6 |
| multiagent | 1 | 1 | 1, 3 |
| files API | 1 | 0 | 8 |
| memory store | 1 | 0 | 2 |
| permission policy | 0 | 0 | — |
| skill | 0 | 0 | — |
