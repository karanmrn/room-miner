# Room Miner

A multi-agent system on **Claude Managed Agents (CMA)** that runs solution-engineer-style discovery calls with founders, reads what they wrote in Linear and Notion, and tells Anthropic developer relations **what founders are stuck on when building managed agents, backed by their own words, with the fix for each.**

A Chief of Staff agent orchestrates nine specialists. Every run is graded three ways (in-run Outcome, post-run trace, post-run recall against a hidden answer key) and costed per agent, so you can tell whether the token spend is worth it.

Built in one session at a Claude event, starting from Anthropic's [`launch-your-agent`](https://github.com/anthropics/launch-your-agent) Claude Code skill. [docs/HOW-WE-BUILT-IT.md](docs/HOW-WE-BUILT-IT.md) walks through the whole process, from the first idea to the first graded run.

---

## What it does

```
                         🤖 chief-of-staff (coordinator, multiagent)
                                    │ send_to_agent, parallel threads
        ┌───────────────┬───────────┴────────────┬──────────────────┐
        ▼               ▼                        ▼                  ▼
 🤖 discovery-agent ×N  🤖 linear-scout      🤖 notion-scout      (relay)
   + 📄 discovery-       reads Linear         reads Notion      🤖 founder-priya
     playbook skill      tickets              pages              🤖 founder-tomas
        │   ▲             │                    │                 🤖 founder-aisha
        │   └── questions/answers relayed ─────┼──────────────── 🤖 founder-ben
        ▼  verbatim by the chief of staff      ▼                 (simulated, evals only)
   calls/*.md, briefs/*.md          evidence/linear.jsonl, evidence/notion.jsonl
        └──────────────────────┬───────────────┘
                               ▼
                         🤖 miner  ──► room-report.md  (ranked pain clusters, verbatim quotes, fix per cluster)
                               ▼
                         🤖 data-analyst ──► data/room.db, data/metrics.json, dashboard.html
                               ▼
                         run-manifest.json + 🧠 run-journal entry
                               ▼   (separate session)
                         🤖 retro ──► method lessons into 🧠 lessons stores ──► next run reads them
```

| Primitive | What we use it for |
|---|---|
| 🤖 Agents (11) | One coordinator, six specialists, four simulated founders. See [docs/AGENTS.md](docs/AGENTS.md). |
| 🧵 Multiagent | `multiagent: {type: "coordinator"}` on the Chief of Staff; parallel discovery calls and scouts |
| 📄 Custom Skill | `discovery-playbook`: Mom Test + SPIN discovery method, needs-brief format, quote discipline |
| 🧠 Memory stores (5) | `pain-library` (clusters across runs), `discovery-lessons`, `scout-lessons`, `coordinator-playbook` (read-only in runs), `run-journal` |
| 🎯 Outcome | 7-criterion rubric, `max_iterations: 3`; the platform grades and the agent revises |
| 📦 Environment | Cloud sandbox, `networking: limited`, no hosts allowed, no package installs |
| 📁 Files API | Seeded Linear and Notion exports mounted read-only; outputs downloaded after each run |
| 🗓️ Deployments | Planned: nightly `room-sweep` and `room-retro` (see [NEXT-DIRECTIONS.md](NEXT-DIRECTIONS.md)) |

---

## Run it

Requirements: an Anthropic API key with Managed Agents access, `bash`, `curl`, `python3` (standard library only), `zip`.

```bash
git clone https://github.com/karanmrn/room-miner.git && cd room-miner
cp .env.example .env && chmod 600 .env      # paste your key after ANTHROPIC_API_KEY=
./launch.sh all                             # model → environment → skill → 5 memory stores → files → 11 agents → first eval run
./launch.sh watch                           # poll until the run finishes (it takes a while; multi-agent relay)
./launch.sh outputs                         # download everything to runs/<session>/
python3 evals/trace_eval.py <session>       # did the chief of staff make the right calls?
python3 evals/score.py <session> case-01    # did it achieve the goal? recall, fabricated quotes, cost per recalled pain
./launch.sh card                            # model, effort, peak context, tokens and cost by agent
open runs/<session>/dashboard.html          # the data-analyst's dashboard
```

`launch.sh` is resumable: every created ID goes into `IDS.env` (gitignored) and each step skips objects that already exist. See [LAUNCH.md](LAUNCH.md) for every command, including `./launch.sh update` to ship a new agent version.

Open `agent-overview.html` in a browser for a live schema of the system (every card is labeled with the real API field behind it).

---

## How it is graded

The eval set is the core of this project: it is how we decide whether a change is an improvement and whether the cost per task is worth paying. Full design in [docs/EVALS.md](docs/EVALS.md).

| Question | Grader | Where |
|---|---|---|
| Did it do the task given? Is everything asked done? | 🎯 Outcome rubric, in the run, graded by the platform; includes the run manifest | `outcome.md` |
| Did it make the right calls? | 🧪 Trace eval over session threads and events | `evals/trace_eval.py` |
| Did it achieve the goal? | 🧪 Recall against a hidden answer key + exact-match fabricated-quote check | `evals/score.py` |
| Is it worth the cost? | 🧪 Scoreboard: `cost_per_recalled_pain`, cost by agent, tokens, effort | `evals/scoreboard.csv` |

The answer key never enters a session. The simulated founders' hidden pains live only in their own agents' system prompts, which no other agent can read.

---

## Repo map

| Path | What it is |
|---|---|
| `agents/*.json` | Agent payloads (model and IDs filled in at launch). `make_founders.py` builds founder agents from persona files. `linear-scout.mcp-v1.json.example` is the real-Linear version for v1. |
| `skills/discovery-playbook/SKILL.md` | The custom Skill attached to the discovery agent |
| `outcome.md` / `first_prompt.txt` | The Outcome rubric and the EVAL-mode kickoff |
| `environment.json` | Sandbox config |
| `evals/case-01/` | Personas, seeded Linear tickets, seeded Notion page, `answer-key.json` |
| `evals/case-02/` | Held-back case (persona template; to be written by someone other than the playbook's author) |
| `evals/trace_eval.py`, `evals/score.py` | Post-run graders |
| `launch.sh`, `LAUNCH.md` | Launch and operate |
| `pricing.json` | Published per-token prices used to split cost by type (the API's `list_cost` stays the authoritative total) |
| `build-sheet.json` | Single source of truth for the design |
| `agent-overview.html` + `overview.css` | Live schema page |
| `NEXT-DIRECTIONS.md` | v1 / v2 plan |
| `runs/` | Real run outputs, committed after scoring |
| `docs/` | How we built it, every agent, eval design |

---

## Status

See [Status and known gaps](docs/HOW-WE-BUILT-IT.md#status-and-known-gaps) for exactly what is done, what is running, and what is still open.

## License

Apache 2.0, see [LICENSE](LICENSE). `overview.css` and the overview page layout come from Anthropic's [`launch-your-agent`](https://github.com/anthropics/launch-your-agent) (Apache 2.0).
