# Needs brief: Ben

**use_case:** A daily agent for a solo, self-funded founder who runs a climate-investor research newsletter. It scans new papers and funding news, picks the items that matter to climate investors, and writes a first draft of the newsletter.

**current_workaround:** Ben does it all by hand: "going through arXiv, a few journals, and funding announcements, and pasting the good bits into a doc. Then I write the thing myself, which eats most of my morning." He can't afford a human intern. He built an agent version a couple of months ago but turned it off after one expensive run, so he's doing the whole thing manually again.

**blockers:**
- **One run cost far more than expected, and nothing capped spend.** "One run went down a rabbit hole and cost me more than the whole previous week. I had no cap on it." / "When you're paying for everything out of your own pocket that really stings"
- **Nothing told the run when to stop and write the draft.** It followed citations with no end: "just kept following the references, paper after paper, reading and summarizing each one." / "so it just kept going."
- **He couldn't see what the run was doing, and found out only afterwards from the bill.** "I only noticed when I checked my bill" / "mostly by scrolling through the output it dumped into my doc that morning, which was this enormous pile of paper summaries. I matched that against the usage on my bill" / "Not exactly scientific, but it got me there."
- **He lost trust, so he turned the agent off, and that costs him time.** "so I shut it off pretty quick after that." / "I'm back to doing the whole scan and write-up by hand, which is a few hours a day I'd rather spend growing the thing." / "I'm not sending as much or as fast as I'd like."
- **Wants editorial taste, but no evidence yet (open question).** "I want it to have taste, you know? Pick the stuff that actually matters to people putting money into climate." We didn't get to day-to-day draft quality. Ben flagged it himself as a gap: "Maybe what the drafts themselves were like, since we mostly talked about that one expensive run and not so much the day-to-day output."

**definition_of_done:** "I'd wake up, grab a coffee, and there'd be a tight draft waiting with the five or six things climate investors actually need to know that day, picked with real taste. I'd spend twenty minutes polishing it, hit send, and use the rest of the morning to grow the business."

**cma_mapping:** (analysis, not quoted)
- Runaway cost → **budget**: a hard spend/token cap on each session, so one run can never cost more than a set amount. Add **webhooks** to alert him when a run nears or hits the cap, not when the monthly bill arrives.
- No stopping point → **outcome**: an explicit completion criterion (a draft with about 5–6 selected items, written to his doc) that ends the session. Back it with a **permission policy** limiting how much citation-following and fetching tools can do per run.
- No visibility → **session**: the session event stream / run history shows what each run did, step by step, and what it cost. **Webhooks** on session completion or failure tell him how each morning's run ended.
- Daily unattended run → **deployment**: scheduled daily trigger for an **agent** defined once. It runs in an **environment** with web/fetch access to arXiv, journals and funding news, and uses an **MCP connector** (or the **files API**) to deliver the draft to his doc. **Vault** holds any source or doc credentials.
- "Taste" (not yet evidenced) → **skill** holding his editorial rubric (what matters to climate investors) plus a **memory store** of past issues and his edits, so selection improves over time. Check draft quality in a follow-up before prioritising this.
- Suggested follow-up: the two gaps Ben named. What the day-to-day drafts were like, and what a working agent is worth to him in dollars (this sets his acceptable per-run budget).
