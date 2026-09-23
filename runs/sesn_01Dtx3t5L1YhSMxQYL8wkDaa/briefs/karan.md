# Needs brief: karan

- **use_case:** An agent (really a set of agents) that turns founder interviews into a prioritized list of product fixes.

- **current_workaround:** Karan reads the interview transcripts in Notion by hand, guesses at priorities, and then often forgets to act on them: "I read transcripts manually in Notion and guess priorities, then i forget and dont fix the bugs or build the features"

- **blockers:**
  - Manual triage gets forgotten and doesn't turn into fixes: "then i forget and dont fix the bugs or build the features"
  - The agent loses track of the task over long runs, from context rot and bad memory: "the agent loses track of what it needs to be done, often context rot and memory gets botched"
  - Work gets routed to the wrong sub-agent: "sometimes calling the wrong agent for the task" / "It sent a placeholder to the wrong agent thread"
  - Debugging is slow because he has to read raw traces: "I lost time digging through the trace to find out what happened"
  - He can't verify that a task really finished, so he doesn't trust the output: "I stopped trusting the result because I couldn't tell if the task was really done"
  - Misrouted runs waste money: "it cost money on a wasted thread."

- **definition_of_done:** "every Monday, a ranked list of the top 3 fixes with quotes, and a check that proves each agent did its job and what it cost."

- **cma_mapping:**
  - Forgetting and manual triage → **deployment** on a weekly (Monday) schedule running the **agent**. A **MCP connector** to Notion to read transcripts. **Outcome** defines the deliverable as a ranked top-3 fix list with quotes. Optionally **webhooks** to push the list to where he'll act on it.
  - Context rot / memory botched → a **memory store** for durable state across runs (pain clusters, past fixes), with a fresh **session** for each run so context stays small. A **skill** holds the ranking method so it isn't re-derived each time.
  - Wrong agent called / placeholder sent to wrong thread → **multiagent** with explicit roles and a routing contract. A **permission policy** limits which agents each one may message or hand off to. The **files API** passes real artifacts between agents instead of placeholders.
  - Digging through traces / can't tell if the task was done → **outcome** with checkable per-agent success criteria, surfaced through the **session** record, and **webhooks** firing on completion or failure.
  - Money wasted on a thread → **budget** per session and per agent, with the cost reported next to each agent's outcome check.
