# Needs brief: Tomas (Patchwork)

- **use_case:** A multi-agent PR review squad for small dev teams (one agent reads the diff, one checks the tests, one writes the review comment) that eventually auto-approves trivial PRs such as dependency bumps and typo fixes.

- **current_workaround:** Four engineers; every PR needs one approval from another engineer. CI runs the test suite, then a human reads the diff and leaves comments on GitHub. When the squad's run stalled, Tomas killed it, read raw logs by hand, and the PR was reviewed manually.

- **blockers:**
  - A sub-agent stalls silently and the coordinator waits forever, with no failure signal: "One of the sub-agents just went quiet and the coordinator kept waiting." / "I could see the coordinator's last message go out, and after that just nothing, no error and no timeout."
  - No way to tell which agent failed or why: "I had no idea which thread died or why." / "In the end I killed the whole run and read through the raw logs trying to piece it together, and I never really found out what happened."
  - Logs can't be attributed per agent, and the coordinator's wait state is invisible: "What I got was one big interleaved stream with no clean way to tell which agent a line belonged to or what the coordinator thought it was waiting on."
  - Because of the above, he doesn't trust it enough to let it act autonomously: "if I can't tell why a run died, I'm not letting it approve anything by itself. So the whole "auto-approve trivial PRs" goal is on hold until I can actually see what each agent is doing."
  - Cost of the last incident: "Mostly an afternoon of digging through logs, and the PR got reviewed by hand anyway."
  - Not a blocker (founder's own view): he says the architecture (splitting the work between agents and the handoffs) is where most of his time went and "That part I'm actually pretty happy with." Asked what else got in the way, he said: "Honestly, nothing that stands out".

- **definition_of_done:** "I'd open a PR and a couple of minutes later there's one clean review comment, with the diff concerns and the test gaps pulled together. The dependency bumps and typo fixes would just get approved and merged without any of us touching them." Precondition for turning on auto-approve: "until I can actually see what each agent is doing."

- **cma_mapping:** (analysis, not quotes)
  - Silent stall / coordinator waits forever → **multiagent** (coordinator and sub-agents as separate threads, each with its own status, so a stalled or idle sub-agent shows up as such instead of blocking unseen) + **session** (session status and events show when a thread goes idle or errors) + **webhooks** (get told about session/thread status changes such as idle, error or terminated instead of polling) + **budget** (caps on turns/tokens/time so a runaway or hung run ends instead of hanging).
  - Can't tell which thread died or why / interleaved logs → **session** event stream with **multiagent** per-thread attribution (each event tied to the agent/thread that produced it, including the coordinator's outgoing messages and pending waits), so he can see each sub-agent's last step directly without scraping raw logs.
  - Trust gate on auto-approval → **outcome** (define "review produced" / "trivial PR approved" as an explicit success condition to check against) + **permission policy** (require human confirmation for the approve/merge tool until trust is built, then loosen it for trivial PR categories) + **MCP connector** (GitHub, for reading diffs, posting comments and approving) + **vault** (holds the GitHub credentials the connector uses).
  - Running it continuously per PR → **deployment** triggered by GitHub PR events, with **agent** definitions for the diff reader, test checker and review writer, plus an **environment** that has the repo and test tooling.
