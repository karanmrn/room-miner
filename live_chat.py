"""Talk to Room Miner yourself. You are the founder; the Chief of Staff relays the discovery
agent's questions to you, then delegates the rest of the pipeline to the other agents.

    python3 live_chat.py start            # create a LIVE session (fixed pipeline), print the first question
    python3 live_chat.py routed           # LIVE-ROUTED: chief of staff picks specialists from what you say
    python3 live_chat.py say "<answer>"   # send your reply, wait, print what happened
    python3 live_chat.py chat             # interactive loop in your own terminal (start + say, repeated)
    python3 live_chat.py watch            # just print new activity until the session waits for you

Every agent handoff is printed as it happens, so you can watch the Chief of Staff delegate.
"""
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
BASE = "https://api.anthropic.com/v1"
STATE = ROOT / "runs" / "live-state.json"
env = {}
for f in (".env", "IDS.env"):
    for line in (ROOT / f).read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
KEY = env["ANTHROPIC_API_KEY"]

KICKOFF = """MODE: LIVE

The human in this session is a real founder. Their slug is "{slug}". Talk to them only by relaying.

1. Run one discovery call with the human. Start one discovery-agent thread for slug "{slug}" and ask it for its first question. Relay each discovery question to the human as your message, exactly as written, starting with "QUESTION:", then end your turn and wait for their reply. Relay each reply back to the same discovery thread, prefixed with "FOUNDER:". Do not start any founder-* agent: the human is the founder.
2. When the discovery agent replies CALL COMPLETE, tell the human in one line that the call is done, then in parallel send linear-scout to read /mnt/session/uploads/linear/tickets.json and notion-scout to read /mnt/session/uploads/notion/office-hours-notes.md.
3. Send the miner everything (the human's call plus the Linear and Notion evidence), and have it write /mnt/session/outputs/room-report.md in EVAL mode.
4. Send the data-analyst the miner's output, and have it build data/room.db, data/metrics.json and /mnt/session/outputs/dashboard.html.
5. Keep /mnt/session/outputs/run-manifest.json current and append this run's entry to the run journal.

Each time you delegate, tell the human in one short line which agent you gave what to. At the end, give the human: their needs brief in three lines, the room clusters their pains belong to, and the one fix that would help them most."""


ROUTED = """MODE: LIVE-ROUTED

The human in this session is a real founder. Their slug is "{slug}". You are an orchestrator: you decide which specialists to bring in, and when, based on what the founder says.

Discovery: start one discovery-agent thread for slug "{slug}" and ask it for its first question. Relay each discovery question to the human as your message, exactly as written, starting with "QUESTION:", then end your turn and wait. Relay each reply back to the same discovery thread, prefixed with "FOUNDER:". Do not start any founder-* agent: the human is the founder.

Routing: after every founder reply, before relaying it, decide whether it triggers a specialist. Specialists and their triggers:
- notion-scout: the founder's evidence, notes or transcripts live in Notion or documents. It reads /mnt/session/uploads/notion/office-hours-notes.md.
- linear-scout: the founder mentions tickets, issues, bug reports, feature requests or Linear. It reads /mnt/session/uploads/linear/tickets.json.
- miner: the founder needs pains clustered, ranked or prioritised across many conversations or sources.
- data-analyst: the founder needs metrics, measurement, dashboards, or a way to tell whether work is done or worth its cost.
Dispatch a specialist the moment its trigger appears, in parallel with the call; do not wait for the call to end. Announce each decision to the human on its own line, exactly in this form:
ROUTING → <agent>: <what you asked it to do> | trigger: "<the founder's exact words>"
Never dispatch a specialist without a trigger in the founder's own words. The miner and data-analyst need evidence first, so give them work only after the call is complete and any scouts you started are done.

When the discovery agent replies CALL COMPLETE, finish the routed work, then give the human:
1. Their needs brief in three lines.
2. A routing table: every specialist, called or not, with the trigger or the reason it was not needed.
3. The top findings and the one fix that would help them most.
Keep /mnt/session/outputs/run-manifest.json current (one entry per specialist you called) and append this run's entry to the run journal."""


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    for k, v in {"x-api-key": KEY, "anthropic-version": "2023-06-01", "anthropic-beta": "managed-agents-2026-04-01",
                 "content-type": "application/json"}.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.JSONDecoder(strict=False).decode(r.read().decode())


def events(sid):
    out, page = [], None
    while True:
        d = call("GET", f"/sessions/{sid}/events?limit=500" + (f"&page={urllib.parse.quote(page)}" if page else ""))
        out += d.get("data", [])
        page = d.get("next_page")
        if not page:
            return out


def state():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def text(e):
    return "".join(c.get("text", "") for c in e.get("content", []) if isinstance(c, dict)).strip()


short = lambda name: (name or "").replace("room-miner-", "")


def show(sid, seen):
    """Print events not seen yet; return True/False on a status change, None if no status event was new."""
    waiting = None
    for e in events(sid):
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        t = e["type"]
        if t == "session.thread_created" and e.get("agent_name") and "chief" not in e["agent_name"]:
            print(f"   🧵 new thread → {short(e['agent_name'])}")
        elif t == "agent.thread_message_sent":
            print(f"   📤 chief-of-staff → {short(e.get('to_agent_name'))}: {text(e)[:110]!r}")
        elif t == "agent.thread_message_received":
            print(f"   📥 {short(e.get('from_agent_name'))} → chief-of-staff: {text(e)[:110]!r}")
        elif t == "agent.message":
            msg = text(e)
            for line in msg.splitlines():
                if line.startswith("ROUTING"):
                    print(f"   🔀 {line}")
            print(f"\n🤖 chief-of-staff: {msg}\n")
        elif t == "span.outcome_evaluation_end":
            print(f"   🎯 grader: {e.get('result')}")
        elif t == "session.status_idle":
            waiting = (e.get("stop_reason") or {}).get("type") == "end_turn"
        elif t == "session.status_running":
            waiting = False
        elif t == "session.error":
            print(f"   ⚠️ {e.get('error')}")
    return waiting


def wait(sid):
    seen = set(state().get("seen", []))
    time.sleep(3)
    waiting = False
    while True:
        w = show(sid, seen)
        if w is not None:
            waiting = w
        st = call("GET", f"/sessions/{sid}")["status"]
        if st in ("idle", "terminated") and (waiting or st == "terminated"):
            break
        time.sleep(4)
    s = state()
    s["seen"] = sorted(seen)
    STATE.write_text(json.dumps(s))
    return st


def start(slug="karan", routed=False):
    ro, rw = "read_only", "read_write"
    mem = [("MEM_PAIN_LIBRARY", rw), ("MEM_RUN_JOURNAL", rw),
           ("MEM_DISCOVERY_LESSONS", ro), ("MEM_SCOUT_LESSONS", ro), ("MEM_COORDINATOR_PLAYBOOK", ro)]
    res = [{"type": "memory_store", "memory_store_id": env[v], "access": a} for v, a in mem]
    res += [{"type": "file", "file_id": env["FILE_LINEAR_CASE01"], "mount_path": "/mnt/session/uploads/linear/tickets.json"},
            {"type": "file", "file_id": env["FILE_NOTION_CASE01"], "mount_path": "/mnt/session/uploads/notion/office-hours-notes.md"}]
    s = call("POST", "/sessions", {
        "agent": env["CHIEF_OF_STAFF_ID"], "environment_id": env["ENV_ID"], "title": f"live {'routed' if routed else 'discovery'}: {slug}",
        "resources": res,
        "initial_events": [{"type": "user.message", "content": [{"type": "text", "text": (ROUTED if routed else KICKOFF).format(slug=slug)}]}]})
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps({"session": s["id"], "seen": []}))
    print(f"▶️  live session {s['id']}")
    print(f"   Console: https://platform.claude.com/workspaces/default/sessions/{s['id']}\n")
    wait(s["id"])


def say(msg):
    sid = state()["session"]
    call("POST", f"/sessions/{sid}/events", {"events": [{"type": "user.message", "content": [{"type": "text", "text": msg}]}]})
    print(f"🧑 you: {msg}")
    return wait(sid)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "chat"
    if cmd in ("start", "routed"):
        start(sys.argv[2] if len(sys.argv) > 2 else "karan", routed=(cmd == "routed"))
    elif cmd == "say":
        say(" ".join(sys.argv[2:]))
    elif cmd == "watch":
        wait(state()["session"])
    elif cmd == "chat":
        if not state().get("session"):
            start()
        while True:
            try:
                msg = input("🧑 you> ").strip()
            except EOFError:
                break
            if msg in ("", "exit", "quit"):
                break
            if say(msg) == "terminated":
                break
