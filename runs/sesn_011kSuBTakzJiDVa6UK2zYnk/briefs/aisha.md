# Needs brief: Aisha (Ledgerline)

- **use_case:** A weekly compliance scan that reviews Ledgerline's flagged SME-payment transactions and drafts the regulator summary for Aisha and her small compliance team. In her words: "It would go through the transactions we've flagged for SME payments and draft the summary we send to the regulator."

- **current_workaround:** It's done by hand. "one of our analysts pulls the flagged transactions every week, goes through them one by one in a spreadsheet, and writes up a draft summary by hand. Then it comes to me." Aisha reviews and edits before it goes out: "So I review it, fix the wording, and only then does it go out. It takes most of a day for the analyst and a couple of hours for me."

- **blockers:**
  - **The agent can't reach the transaction database inside their private network (VPC).** This is the main blocker and the reason the prototype stopped: "Our transaction DB sits inside our VPC. The agent runs in the cloud, so it just couldn't reach it and I gave up."
  - **She won't expose the database to the internet to get access.** "I wasn't comfortable opening the database up to the internet just to test an idea, so it stopped there." and "opening anything in our VPC to the outside isn't something I'd do lightly for a test."
  - **The manual-export workaround isn't worth it.** "a manual export every week defeats the purpose, so I stopped there."
  - **The drafting has never been tested on a full week of data** (this follows from the access blocker; drafting on a small sample went well): "But it was a small sample, so I never got to see how it would do on a real week."
  - **Hard constraint: a human must approve before anything reaches the regulator.** "Nothing goes to the regulator without me reading it. If the agent could send on its own, legal would shut it down on day one."
  - **Hard constraint: she has to be able to explain and trust the system.** "anything touching our data or our regulator has to be something I can explain and stand behind." and "I'd rather it be slow and right than fast and wrong."

- **definition_of_done:** "On Monday morning I'd open a finished draft of the regulator summary, with the flagged transactions already reviewed and the important ones called out. My analyst would get the day back for real investigative work". Aisha still reviews the draft and sends it herself.

- **cma_mapping:** (analysis, not quoted)
  - *VPC database access without opening it to the internet* → an **MCP connector** to a self-hosted MCP server that runs inside Ledgerline's VPC and makes only outbound connections. It exposes a narrow, read-only "fetch flagged transactions for week X" tool rather than the raw database. Database credentials go in a **vault** and are never put in the prompt. The **environment** has network access limited to that connector.
  - *No weekly manual export* → a scheduled **deployment** that starts one **session** per week and pulls the data through the connector. **Webhooks** tell Aisha when the draft is ready for Monday morning.
  - *Human approval before sending, and nothing sent on its own* → a **permission policy** that allows only read-only data tools and has no tool for sending to the regulator or any outside party. The deliverable is a draft file delivered through the **files API** for Aisha to review. An **outcome** defines "draft ready for review" as the success state, not "submitted".
  - *Draft quality on a full week, and trust she can explain* → a **skill** that holds the regulator-summary template, the house style and the criteria for which transactions to highlight. A **memory store** keeps her past wording corrections so her edits get smaller each week. Session logs and transcripts show which transactions were reviewed and why items were called out, which supports "explain and stand behind". A **budget** caps the weekly run's cost.
  - *Not needed now:* **multiagent**. One agent covers the single weekly scan-and-draft job. Only revisit it if the scan and drafting later need to be split up.
