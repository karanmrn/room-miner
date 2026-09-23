# Needs brief: Priya (Lumen Skin)

**use_case:** An agent that runs overnight as an ops manager for Lumen Skin, a nine-person DTC skincare brand. It checks Shopify inventory against each supplier's lead time and drafts reorder emails to suppliers.

**current_workaround:** Priya does it herself, late at night. In her words: "I pull up Shopify, eyeball what's running low, work out in my head which suppliers are slow, and write the emails myself." Supplier lead times only exist in her head. After the agent's reports went stale she went back to this manual process ("So I was basically doing the job twice for a while.").

**blockers:**
- She didn't know where to put the Shopify credential, so she put it in the prompt: "I literally pasted my Shopify key into the prompt because I couldn't figure out where else it goes." She did look for the right place first: "I poked around looking for somewhere obvious to put it, didn't find anything that made sense to me, and I was tired."
- Connecting to Shopify at all was the first obstacle: "Getting it hooked up to Shopify was the first wall."
- The nightly scheduled run kept replaying a date she had hardcoded, so every report was stale: "It ran every night but kept checking stock for the 14th. I'd typed the date into the task and it just replayed it forever."
- She lost trust in the agent's output and went back to doing it by hand: "Once I noticed, I stopped believing anything it told me and went back to checking Shopify myself at night."

**definition_of_done:** "I'd wake up to a short list of what's running low today, which suppliers need to hear from us given their lead times, and the reorder emails already drafted. I'd just skim, hit send, and get on with my day." She keeps the final send herself. That differs from her opening wish: "It would be amazing if it could just email suppliers for me."

**cma_mapping:**
- Shopify key in the prompt → **vault** to store the Shopify credential, injected at runtime and never placed in the prompt or agent config.
- Hooking up to Shopify → **MCP connector** for Shopify (inventory read), with its auth drawn from the vault.
- Stale hardcoded date on nightly runs → **deployment** on a nightly schedule that starts a fresh **session** each run. The run date and "today" context get passed in at session start, not baked into the **agent** definition or task text.
- Lost trust / stale report → **outcome** that defines what a valid morning report is (dated today, current stock levels, list of suppliers to contact), so a stale or malformed run shows up as a failure. Optionally **webhooks** to alert her when a run fails or doesn't meet the outcome.
- Supplier lead times live only in her head → **memory store** (or a **files API** upload) holding supplier lead times, so the agent can reason about "which suppliers need to hear from us given their lead times".
- Draft vs. send → **permission policy** that lets the agent draft emails but requires her approval to send. This matches her definition of done ("skim, hit send"). Sending could be loosened later if she wants the "just email suppliers for me" version.
- Reorder logic (low stock vs. lead time, email drafting format) → a **skill** holding the reorder procedure and email template.

**open questions (not covered in the call):** where supplier lead-time data would come from, which email system the drafts should land in, and how many SKUs and suppliers are involved.
