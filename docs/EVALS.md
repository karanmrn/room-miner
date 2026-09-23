# Evals

Evals are the most important part of this project. They answer two questions for every agent version: **is it doing the job**, and **is the token cost per task worth paying**.

## Four questions, four graders

| Question | Grader | When | How |
|---|---|---|---|
| Did it do the task given? Is everything asked done? | 🎯 **Outcome** (`outcome.md`) | In the run | The platform grades 7 binary criteria against the outputs; the agent revises until satisfied or `max_iterations: 3` |
| Did it make the right calls? | 🧪 **Trace eval** (`evals/trace_eval.py`) | After the run | Reads threads and events through the API |
| Did it achieve the goal? | 🧪 **Recall + faithfulness** (`evals/score.py`) | After the run | Answer key + exact-match quote check |
| Is it worth the cost? | 🧪 **Scoreboard** (`evals/scoreboard.csv`) | After the run | Cost per recalled pain, cost by agent |

A single Outcome rubric cannot answer all four: the Outcome grader sees output files, not who called whom, and the agent can read the rubric, so it must never contain the answers.

## 🎯 Outcome rubric (in-run)

1. At least 5 pain clusters, ranked by distinct founders.
2. 2+ verbatim quotes per cluster, each tagged with source and link.
3. Every quoted string appears character for character in an evidence item.
4. Evidence from `call`, `linear` and `notion` all appears.
5. Every founder has a 5-field needs brief with real CMA primitive names.
6. Every cluster ends with a concrete fix; the report ends with a blocker tally by primitive.
7. `run-manifest.json` has a `done` entry with existing outputs for every kickoff step; the dashboard's numbers all appear in `metrics.json`.

## 🧪 Trace eval: "made the right calls"

| Check | Why |
|---|---|
| Exactly one thread per founder | A message sent to an agent instead of its thread starts a new, empty instance (caught in run 1) |
| One discovery thread per founder | Every founder was interviewed, once |
| linear-scout, notion-scout, miner, data-analyst each dispatched | Nothing skipped |
| Miner started after both scouts; data-analyst after the miner | Merge order is right |
| No unexpected agents | No stray work |
| Questions relayed verbatim; answers relayed verbatim | The coordinator is a neutral wire; paraphrase would contaminate the evidence |
| At most 8 questions per call | Playbook budget |
| Manifest: every step `done`, and every delegate it names actually ran | "Done" claims match reality |

## 🧪 Recall and faithfulness: "achieved the goal"

- `evals/case-01/answer-key.json` lists 12 hidden pains across 4 founder calls, 5 Linear tickets and a Notion page, each tagged with the CMA primitive involved. It is read only on your machine and never enters a session.
- **Recall:** a separate model (`claude-sonnet-5`) judges, per hidden pain, whether the report surfaces the same underlying problem with a supporting quote.
- **Fabricated quotes:** every quoted string in the report and briefs must appear in the evidence or transcripts (exact match after whitespace and apostrophe normalization). No model involved.
- **Relay fidelity:** each persona's verbatim line that was revealed must appear word for word in the transcript.
- **Pass bar:** recall of at least 80% and 0 fabricated quotes.

## 💵 Scoreboard: "worth the cost"

One row per scored run in `evals/scoreboard.csv`:

`run_at, case, session, agent_version, outcome, trace_pass, recall, fabricated_quotes, relay_exact, tokens_in, tokens_out, cost_usd, active_s, cost_per_recalled_pain`

- `cost_usd` comes from the API's `list_cost` (authoritative). `./launch.sh card` also splits it by token type using `pricing.json` and by agent using per-thread usage.
- **`cost_per_recalled_pain`** is the headline: dollars per real insight surfaced. Use it to compare versions and settings (for example, does `medium` effort on the discovery agent keep recall at 80% or more while cutting cost?).

## Held-back case and the learning claim

- `evals/case-02/` is held back: never used while iterating, only to check that a new version did not regress.
- Its personas should be written by someone other than the author of the discovery playbook, so the test is not circular (template in `evals/case-02/personas/TEMPLATE.md`).
- The retro loop writes lessons after every run. Recall rising on case-01 alone does not prove learning, because case-01 is what the lessons were written from. Only claim improvement when case-02 also holds or improves. Eval runs mount every memory store `read_only` so held-back cases cannot be memorized.
