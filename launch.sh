#!/usr/bin/env bash
# Room Miner launch sequence. One API call (or one object) per step, resumable:
# every step reads IDS.env first and skips objects that already exist.
#
#   ./launch.sh all          # models -> env -> skill -> memory -> files -> agents -> run
#   ./launch.sh <step>       # models | env | skill | memory | files | agents | run | status | watch | card | outputs | deploy | fire SWEEP|RETRO | get <path>
#
# The API key is loaded from .env and never printed.
set -euo pipefail
cd "$(dirname "$0")"

BASE=https://api.anthropic.com/v1
export TMP="${TMPDIR:-/tmp}/room-miner"; mkdir -p "$TMP"
touch IDS.env

load() {
  set -a; . ./.env; [ -s IDS.env ] && . ./IDS.env; set +a
  if [ -z "${ANTHROPIC_API_KEY:-}" ]; then echo "ANTHROPIC_API_KEY missing: put it in $(pwd)/.env"; exit 1; fi
}

save() {  # save KEY VALUE into IDS.env (replacing any old value)
  grep -v "^$1=" IDS.env > "$TMP/ids" || true; echo "$1=$2" >> "$TMP/ids"; mv "$TMP/ids" IDS.env
  export "$1=$2"
}

# api METHOD PATH [json-body-file] [beta-header]  -> response in $TMP/resp.json, exits on HTTP >= 400
api() {
  local method=$1 path=$2 body=${3:-} beta=${4-managed-agents-2026-04-01}
  local args=(-sS -X "$method" "$BASE$path" -o "$TMP/resp.json" -w '%{http_code}'
    -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" -H "content-type: application/json")
  [ -n "$beta" ] && args+=(-H "anthropic-beta: $beta")
  [ -n "$body" ] && args+=(--data @"$body")
  local code; code=$(curl "${args[@]}")
  if [ "$code" -ge 400 ]; then echo "HTTP $code on $method $path"; cat "$TMP/resp.json"; echo; exit 1; fi
}

get_quiet() {  # get_quiet PATH OUTFILE: GET without exiting on error (writes {} on failure)
  curl -sS -f "$BASE$1" -o "$2" -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" \
    -H "anthropic-beta: managed-agents-2026-04-01" 2>/dev/null || echo '{}' > "$2"
}

field() {  # field <python expr on d>, parsed with strict=False (system prompts contain control chars)
  python3 -c "import json; d=json.JSONDecoder(strict=False).decode(open('$TMP/resp.json').read()); print($1)"
}

step_models() {
  [ -n "${MODEL:-}" ] && { echo "✓ model $MODEL (saved)"; return; }
  api GET /models "" ""
  local m; m=$(field "next(x['id'] for x in d['data'] if 'opus' in x['id'])")
  save MODEL "$m"; echo "✓ model $MODEL (newest Opus-class available to this key)"
}

step_env() {
  [ -n "${ENV_ID:-}" ] && { echo "✓ 📦 environment $ENV_ID (exists)"; return; }
  api POST /environments environment.json
  save ENV_ID "$(field "d['id']")"; echo "✅ 📦 environment $ENV_ID"
}

step_skill() {
  [ -n "${DISCOVERY_SKILL_ID:-}" ] && { echo "✓ 📄 skill $DISCOVERY_SKILL_ID (exists)"; return; }
  (cd skills && rm -f "$TMP/discovery-playbook.zip" && zip -qr "$TMP/discovery-playbook.zip" discovery-playbook)
  local code; code=$(curl -sS -X POST "$BASE/skills" -o "$TMP/resp.json" -w '%{http_code}' \
    -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" \
    -F "files[]=@$TMP/discovery-playbook.zip")
  if [ "$code" -ge 400 ]; then echo "HTTP $code on POST /skills"; cat "$TMP/resp.json"; echo; exit 1; fi
  save DISCOVERY_SKILL_ID "$(field "d['id']")"; echo "✅ 📄 skill discovery-playbook $DISCOVERY_SKILL_ID"
}

step_memory() {
  local stores=(
    "MEM_PAIN_LIBRARY|room-miner-pain-library|Cumulative founder pain clusters (one file per cluster) with founder counts and first/last seen. Owned by the miner."
    "MEM_DISCOVERY_LESSONS|room-miner-discovery-lessons|Method lessons for discovery calls: question patterns that surfaced pains or fell flat. Written only by the retro."
    "MEM_SCOUT_LESSONS|room-miner-scout-lessons|Method lessons for the Linear and Notion scouts: source quirks and what counts as evidence. Written only by the retro."
    "MEM_COORDINATOR_PLAYBOOK|room-miner-coordinator-playbook|Dispatch, relay, merge and clustering lessons for the Chief of Staff and miner. Written only by the retro."
    "MEM_RUN_JOURNAL|room-miner-run-journal|One factual entry per run: what was dispatched, what came back, what went wrong, grader feedback. Read by the retro."
  )
  for s in "${stores[@]}"; do
    IFS='|' read -r var name desc <<< "$s"
    if [ -n "${!var:-}" ]; then echo "✓ 🧠 $name ${!var} (exists)"; continue; fi
    python3 -c "import json,sys; json.dump({'name':sys.argv[1],'description':sys.argv[2]}, open('$TMP/body.json','w'))" "$name" "$desc"
    api POST /memory_stores "$TMP/body.json" agent-memory-2026-07-22
    save "$var" "$(field "d['id']")"; echo "✅ 🧠 $name ${!var}"
  done
}

step_files() {
  upload() {  # upload VAR PATH
    if [ -n "${!1:-}" ]; then echo "✓ file $2 ${!1} (exists)"; return; fi
    local code; code=$(curl -sS -X POST "$BASE/files" -o "$TMP/resp.json" -w '%{http_code}' \
      -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" -F "file=@$2")
    if [ "$code" -ge 400 ]; then echo "HTTP $code uploading $2"; cat "$TMP/resp.json"; echo; exit 1; fi
    save "$1" "$(field "d['id']")"; echo "✅ file $2 ${!1}"
  }
  upload FILE_LINEAR_CASE01 evals/case-01/linear/tickets.json
  upload FILE_NOTION_CASE01 evals/case-01/notion/office-hours-notes.md
}

# render <payload.json> <effort> -> $TMP/body.json with model + $PLACEHOLDERS filled from the environment
render() {
  python3 - "$1" "$2" <<'PY'
import json, os, re, sys
d = json.load(open(sys.argv[1]))
d["model"] = {"id": os.environ["MODEL"], "effort": sys.argv[2]}
s = json.dumps(d)
missing = sorted({m for m in re.findall(r"\$([A-Z_]+)", s) if m not in os.environ})
if missing:
    sys.exit(f"missing IDs for {sys.argv[1]}: {missing}")
s = re.sub(r"\$([A-Z_]+)", lambda m: os.environ[m.group(1)], s)
open(os.path.join(os.environ["TMP"], "body.json"), "w").write(s)
PY
}

create_agent() {  # create_agent VAR payload effort
  local var=$1 file=$2 effort=$3
  if [ -n "${!var:-}" ]; then echo "✓ 🤖 $(basename "$file" .json) ${!var} (exists)"; return; fi
  TMP="$TMP" render "$file" "$effort"
  api POST /agents "$TMP/body.json"
  save "$var" "$(field "d['id']")"; save "${var%_ID}_VERSION" "$(field "d['version']")"
  echo "✅ 🤖 $(basename "$file" .json) ${!var} (v$(field "d['version']"), $MODEL, effort $effort)"
}

update_agent() {  # update_agent VAR payload effort: new version of an existing agent (same ID)
  local var=$1 file=$2 effort=$3 vvar="${1%_ID}_VERSION"
  TMP="$TMP" render "$file" "$effort"
  python3 -c "import json,os; p=os.environ['TMP']+'/body.json'; d=json.load(open(p)); d['version']=int(os.environ['$vvar']); json.dump(d,open(p,'w'))"
  api POST "/agents/${!var}" "$TMP/body.json"
  save "$vvar" "$(field "d['version']")"
  echo "✅ 🤖 $(basename "$file" .json) ${!var} → v${!vvar}"
}

step_agents() {
  python3 agents/make_founders.py evals/case-01/personas >/dev/null
  create_agent DISCOVERY_AGENT_ID agents/discovery-agent.json high
  create_agent LINEAR_SCOUT_ID    agents/linear-scout.json    medium
  create_agent NOTION_SCOUT_ID    agents/notion-scout.json    medium
  create_agent MINER_ID           agents/miner.json           high
  create_agent DATA_ANALYST_ID    agents/data-analyst.json    high
  create_agent RETRO_ID           agents/retro.json           high
  for f in priya tomas aisha ben; do
    create_agent "FOUNDER_$(echo $f | tr a-z A-Z)_ID" "agents/founder-$f.json" medium
  done
  create_agent CHIEF_OF_STAFF_ID  agents/chief-of-staff.json  high
}

step_run() {  # starts a new graded EVAL session every time it is called
  python3 - <<'PY' > "$TMP/body.json"
import json, os
ro, rw = "read_only", "read_write"
mem = [("MEM_PAIN_LIBRARY", rw), ("MEM_RUN_JOURNAL", rw),
       ("MEM_DISCOVERY_LESSONS", ro), ("MEM_SCOUT_LESSONS", ro), ("MEM_COORDINATOR_PLAYBOOK", ro)]
resources = [{"type": "memory_store", "memory_store_id": os.environ[v], "access": a} for v, a in mem]
resources += [
    {"type": "file", "file_id": os.environ["FILE_LINEAR_CASE01"], "mount_path": "/mnt/session/uploads/linear/tickets.json"},
    {"type": "file", "file_id": os.environ["FILE_NOTION_CASE01"], "mount_path": "/mnt/session/uploads/notion/office-hours-notes.md"},
]
kickoff = {"type": "user.define_outcome", "description": open("first_prompt.txt").read(),
           "rubric": {"type": "text", "content": open("outcome.md").read()}, "max_iterations": 3}
print(json.dumps({"agent": os.environ["CHIEF_OF_STAFF_ID"], "environment_id": os.environ["ENV_ID"],
                  "title": "case-01 eval", "resources": resources, "initial_events": [kickoff]}))
PY
  api POST /sessions "$TMP/body.json"
  save SESSION_ID "$(field "d['id']")"
  echo "$(date -u +%FT%TZ) case-01 $SESSION_ID agent=$CHIEF_OF_STAFF_ID v$CHIEF_OF_STAFF_VERSION" >> runs.log
  echo "✅ ▶️ run started $SESSION_ID"
  echo "   Console: https://platform.claude.com/workspaces/${WORKSPACE:-default}/sessions/$SESSION_ID"
}

step_status() {
  api GET "/sessions/${1:-$SESSION_ID}"
  field "d['status'] + '  outcome: ' + (', '.join(e.get('result','?') for e in d.get('outcome_evaluations') or []) or 'not graded yet')"
}

step_watch() {  # poll until the session leaves 'running'
  while :; do
    local line; line=$(step_status "${1:-$SESSION_ID}")
    echo "$(date +%T)  $line"
    case "$line" in running*|rescheduling*) sleep 30 ;; *) break ;; esac
  done
}

step_card() {  # model, effort, context, tokens and cost for one session
  local sid=${1:-$SESSION_ID}
  api GET "/sessions/$sid"; cp "$TMP/resp.json" "$TMP/session.json"
  # threads and events are best effort: a missing endpoint or param must not break the card
  get_quiet "/sessions/$sid/threads" "$TMP/threads.json"
  get_quiet "/sessions/$sid/events?limit=1000&types[]=span.model_request_end" "$TMP/events.json"
  python3 - "$TMP" <<'PY'
import json, os, sys
tmp = sys.argv[1]
load = lambda n: json.JSONDecoder(strict=False).decode(open(os.path.join(tmp, n)).read())
s, prices = load("session.json"), json.load(open("pricing.json"))
model = os.environ["MODEL"]; p = prices["usd_per_mtok"].get(model)
u = s.get("usage") or {}
cw = u.get("cache_creation_input_tokens", 0)
if isinstance(u.get("cache_creation"), dict):
    cw = sum(v for v in u["cache_creation"].values() if isinstance(v, (int, float)))
toks = {"input": u.get("input_tokens", 0), "cache_write": cw,
        "cache_read": u.get("cache_read_input_tokens", 0), "output": u.get("output_tokens", 0)}
secs = u.get("active_seconds") or s.get("stats", {}).get("active_seconds") or 0
lc = u.get("list_cost") or s.get("list_cost")
peak = 0  # peak context: largest single model request seen in the event stream (best effort)
try:
    for e in load("events.json").get("data", []):
        eu = e.get("model_usage") if e.get("type") == "span.model_request_end" else None
        if isinstance(eu, dict):
            peak = max(peak, eu.get("input_tokens", 0) + eu.get("cache_read_input_tokens", 0) + eu.get("cache_creation_input_tokens", 0))
except Exception:
    pass
print(f"\n  ▶️ session        {s['id']}   status {s['status']}")
print(f"  🤖 model          {model}")
eff = json.load(open("build-sheet.json")).get("effort", {})
print("  ⚙️ effort         " + ", ".join(f"{k} {v}" for k, v in eff.items()))
print(f"  🧠 context        peak {peak:,} tokens in one coordinator request" if peak else "  🧠 context        not exposed per request in this session's events")
print(f"  ⏱  active         {secs:,.0f} s")
print("  tokens            " + "  ".join(f"{k} {v:,}" for k, v in toks.items()))
if p:
    cost = {"input": toks["input"] * p["input"], "cache_write": toks["cache_write"] * p["cache_write_5m"],
            "cache_read": toks["cache_read"] * p["cache_read"], "output": toks["output"] * p["output"]}
    cost = {k: v / 1e6 for k, v in cost.items()}
    cost["runtime"] = secs / 3600 * prices["session_runtime_usd_per_hour"]
    print("  💵 cost (est.)    " + "  ".join(f"{k} ${v:.3f}" for k, v in cost.items()) + f"   = ${sum(cost.values()):.3f}")
if lc:
    print(f"  💵 list_cost      {lc}   (API total, authoritative)")
try:
    th = load("threads.json").get("data", [])
    if th:
        agg = {}
        for t in th:
            tu, name = t.get("usage") or {}, t["agent"]["name"].removeprefix("room-miner-")
            cc = sum((tu.get("cache_creation") or {}).values()) if isinstance(tu.get("cache_creation"), dict) else 0
            a = agg.setdefault(name, {"threads": 0, "in": 0, "out": 0, "cents": 0})
            a["threads"] += 1; a["out"] += tu.get("output_tokens", 0)
            a["in"] += tu.get("input_tokens", 0) + tu.get("cache_read_input_tokens", 0) + cc
            a["cents"] += int((tu.get("list_cost") or {}).get("amount", 0))
        print(f"  🧵 by agent       {len(th)} threads")
        for name, a in sorted(agg.items(), key=lambda kv: -kv[1]["cents"]):
            print(f"     {name:18} ×{a['threads']:<2} in {a['in']:>9,}  out {a['out']:>7,}  ${a['cents']/100:.2f}")
except Exception:
    pass
print()
PY
}

step_outputs() {  # download every output file (all pages), then sort them back into calls/ briefs/ evidence/
  local sid=${1:-$SESSION_ID}
  python3 evals/fetch_outputs.py "$sid"
}

step_deploy() {  # nightly room-sweep (chief of staff, SWEEP) + room-retro (retro), Europe/London
  python3 - <<'PY' > "$TMP/sweep.json"
import json, os
ro, rw = "read_only", "read_write"
mem = [("MEM_PAIN_LIBRARY", rw), ("MEM_RUN_JOURNAL", rw),
       ("MEM_DISCOVERY_LESSONS", ro), ("MEM_SCOUT_LESSONS", ro), ("MEM_COORDINATOR_PLAYBOOK", ro)]
res = [{"type": "memory_store", "memory_store_id": os.environ[v], "access": a} for v, a in mem]
res += [{"type": "file", "file_id": os.environ["FILE_LINEAR_CASE01"], "mount_path": "/mnt/session/uploads/linear/tickets.json"},
        {"type": "file", "file_id": os.environ["FILE_NOTION_CASE01"], "mount_path": "/mnt/session/uploads/notion/office-hours-notes.md"}]
ev = {"type": "user.define_outcome", "description": open("deploy/sweep_prompt.md").read(),
      "rubric": {"type": "text", "content": open("deploy/sweep_outcome.md").read()}, "max_iterations": 3}
print(json.dumps({"name": "room-sweep", "agent": os.environ["CHIEF_OF_STAFF_ID"], "environment_id": os.environ["ENV_ID"],
                  "resources": res, "initial_events": [ev],
                  "schedule": {"type": "cron", "expression": "0 21 * * *", "timezone": "Europe/London"}}))
PY
  python3 - <<'PY' > "$TMP/retro.json"
import json, os
ro, rw = "read_only", "read_write"
mem = [("MEM_RUN_JOURNAL", ro), ("MEM_DISCOVERY_LESSONS", rw), ("MEM_SCOUT_LESSONS", rw), ("MEM_COORDINATOR_PLAYBOOK", rw)]
res = [{"type": "memory_store", "memory_store_id": os.environ[v], "access": a} for v, a in mem]
ev = {"type": "user.message", "content": [{"type": "text", "text": open("deploy/retro_prompt.md").read()}]}
print(json.dumps({"name": "room-retro", "agent": os.environ["RETRO_ID"], "environment_id": os.environ["ENV_ID"],
                  "resources": res, "initial_events": [ev],
                  "schedule": {"type": "cron", "expression": "0 22 * * *", "timezone": "Europe/London"}}))
PY
  for d in SWEEP:sweep RETRO:retro; do
    local var="DEPLOY_${d%%:*}_ID" file="$TMP/${d##*:}.json"
    if [ -n "${!var:-}" ]; then echo "✓ 🗓️ ${d##*:} ${!var} (exists)"; continue; fi
    api POST "/deployments?beta=true" "$file"
    save "$var" "$(field "d['id']")"
    echo "✅ 🗓️ room-${d##*:} ${!var}  next: $(field "', '.join((d.get('schedule') or {}).get('upcoming_runs_at', [])[:2])")"
    echo "   Console: https://platform.claude.com/workspaces/${WORKSPACE:-default}/deployments/${!var}"
  done
}

step_fire() {  # manual run of a deployment now: ./launch.sh fire SWEEP|RETRO
  local var="DEPLOY_${1:-SWEEP}_ID"
  api POST "/deployments/${!var}/run?beta=true" <(echo '{}')
  field "json.dumps({k: d.get(k) for k in ('id', 'session_id', 'status') if k in d})"
}

load
case "${1:-all}" in
  all)     step_models; step_env; step_skill; step_memory; step_files; step_agents; step_run ;;
  models)  step_models ;;  env) step_env ;;  skill) step_skill ;;  memory) step_memory ;;
  files)   step_files ;;   agents) step_agents ;;  run) step_run ;;
  status)  step_status "${2:-}" ;;  watch) step_watch "${2:-}" ;;
  card)    step_card "${2:-}" ;;    outputs) step_outputs "${2:-}" ;;
  update)  # ./launch.sh update VAR payload effort ; then refresh the coordinator so its roster picks up the new version
           update_agent "$2" "$3" "$4"
           if [ "$2" != CHIEF_OF_STAFF_ID ]; then update_agent CHIEF_OF_STAFF_ID agents/chief-of-staff.json high; fi ;;
  deploy)  step_deploy ;;  fire) step_fire "${2:-SWEEP}" ;;
  get)     api GET "$2"; python3 -c "import json; print(json.dumps(json.JSONDecoder(strict=False).decode(open('$TMP/resp.json').read()), indent=1)[:${3:-4000}])" ;;
  *) echo "unknown step: $1"; exit 1 ;;
esac
