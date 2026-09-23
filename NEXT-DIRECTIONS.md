# Next directions

Everything that is deliberately not in v0, slotted into planned versions. Each item: what / why deferred / how.

## v1

### 1. Real founders instead of simulated personas
- **What:** Real founders talk to the discovery agent directly.
- **Why deferred:** Out of scope for v0. A live back-and-forth with a human needs an interface on top of Sessions; v0 proves the pipeline with graded synthetic personas first.
- **How:** A small chat surface where each founder conversation is one Session on the discovery agent (the slack_data_bot pattern: sessions as conversations). Transcripts then flow to the miner unchanged.

### 2. Linear for real (hosted MCP)
- **What:** linear-scout reads the live "Founder Feedback Demo" team through the hosted Linear MCP server instead of the mounted export.
- **Why deferred:** Needs a credential not on hand (founder chose not to create a Linear personal API key for v0).
- **How:** Create a Linear personal API key, store it as a `static_bearer` vault credential keyed to `https://mcp.linear.app/mcp`, create the agent from `agents/linear-scout.mcp-v1.json.example` (read tools only, `always_allow`), set the environment's `allow_mcp_servers: true`, and pass `vault_ids` at session and deployment creation. Evidence format unchanged.

### 2b. Notion for real
- **What:** notion-scout reads the live Notion page instead of the seeded export.
- **Why deferred:** Needs a credential not on hand (Notion internal integration token).
- **How:** Create an internal integration (notion.so/profile/integrations, "Read content" only), add it to the demo page via Connections, store it as an `environment_variable` vault credential `NOTION_API_KEY` locked to `api.notion.com` with `injection_location: {header: true}`, add `api.notion.com` to the environment's `allowed_hosts`, and point the scout at the API. Output format unchanged.

### 3. Move notion-scout to the hosted Notion MCP connector
- **What:** notion-scout uses the hosted Notion MCP server instead of direct REST calls.
- **Why deferred:** Out of scope for v0. Notion's hosted MCP accepts only OAuth, so it needs an `mcp_oauth` credential (a full OAuth flow plus refresh); the integration-token route in #2 is simpler and lower risk.
- **How:** Add `mcp_servers[]` + an `mcp_toolset` entry to notion-scout, run the OAuth flow once, store an `mcp_oauth` credential (with `refresh` block) in the same vault keyed by the server URL, then archive the `NOTION_API_KEY` credential. Evidence format and miner stay unchanged. Docs: https://platform.claude.com/docs/en/managed-agents/vaults

### 4. Wispr Flow voice notes as a source
- **What:** A voice-notes scout turns Wispr Flow transcripts into evidence items.
- **Why deferred:** Out of scope for v0 (founder chose to skip). No Wispr Flow MCP server is known, so this is a file route.
- **How:** Export transcripts, upload via the Files API, mount under `/mnt/session/uploads/wispr/`, add a `voice-notes-scout` to the chief-of-staff roster.

### 5. Two-batch Linear seed for the nightly story
- **What:** Seed a second batch of founder tickets between sweeps so the nightly digest shows genuinely new and growing pains.
- **Why deferred:** Out of scope for v0 (founder chose to skip for now).
- **How:** Split `evals/case-01/linear/tickets.json` into batch A (before sweep 1) and batch B (after); create batch B via the Linear connector, then trigger `room-sweep` with a manual run.

### 6. Room report on the overview page
- **What:** Render the latest `room-report.md` into `agent-overview.html` after each run.
- **Why deferred:** Out of scope for v0 (founder chose to skip for now). This is the generated-interface extension.
- **How:** After each run, fetch outputs via `GET /v1/files?scope_id=<session>` and write the top clusters into a report slot on the page.

### 7. Prove learning generalises
- **What:** Report case-02 recall before and after retros alongside case-01.
- **Why deferred:** Process habit; the claim is invalid without it.
- **How:** `evals/run-evals.sh` runs both cases per agent version with every memory store mounted read_only.

### 8. trace-auditor specialist
- **What:** A specialist that reads another run's threads and events and reports wrong calls, stray threads, lost context and cost per agent, in plain language.
- **Why deferred:** Out of scope for v0. Surfaced live in discovery: the founder's own pain was "sometimes calling the wrong agent for the task" and "I couldn't tell if the task was really done", which no roster agent covers today.
- **How:** Wrap `evals/trace_eval.py`'s checks as instructions for a new roster agent with read-only access to a mounted export of the session's threads and events; route to it on triggers like "wrong agent", "lost track", "is it done".

### 9. Keep folder layout in outputs
- **What:** The chief of staff zips `/mnt/session/outputs/` into `bundle.zip` (Python `zipfile`) at the end of every run.
- **Why deferred:** Found in run 1: the Files API keeps bare filenames only, so four `transcript.md` files collide. `evals/fetch_outputs.py` rebuilds the layout by content as a workaround.
- **How:** One line in the chief of staff's end-of-run instructions (v4); `fetch_outputs.py` unzips `bundle.zip` when present.

## v2

### 10. Resolve the same founder across sources
- **What:** Recognise that "@karan" in Linear, "Karan M." in Notion and a call transcript are the same person, and merge their evidence.
- **Why deferred:** Out of scope for v0. Identity resolution is its own hard problem; v0 keeps founders distinct per source.
- **How:** An identity step in the miner (or a small resolver specialist) that keys on email/handle where available and fuzzy name + context otherwise, with an `unresolved` bucket rather than guessing. Store resolved identities in the `pain-library` memory store.
