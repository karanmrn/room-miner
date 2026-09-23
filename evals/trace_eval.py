"""Trace eval: did the Chief of Staff make the right calls? Reads a finished session's threads and events.

    python3 evals/trace_eval.py <session_id> [founder-slug ...]     (default founders: priya tomas aisha ben)

Writes runs/<session_id>/trace-eval.json (score.py folds its pass/fail into the scoreboard).
"""
import json
import pathlib
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://api.anthropic.com/v1"
KEY = next(l.split("=", 1)[1].strip() for l in (ROOT / ".env").read_text().splitlines() if l.startswith("ANTHROPIC_API_KEY="))
P = "room-miner-"


def get(path):
    req = urllib.request.Request(BASE + path)
    for k, v in {"x-api-key": KEY, "anthropic-version": "2023-06-01", "anthropic-beta": "managed-agents-2026-04-01"}.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.JSONDecoder(strict=False).decode(r.read().decode())


def all_pages(path):
    items, page = [], None
    while True:
        sep = "&" if "?" in path else "?"
        d = get(path + (f"{sep}page={urllib.parse.quote(page)}" if page else ""))
        items += d.get("data", [])
        page = d.get("next_page")
        if not page:
            return items


text = lambda e: "".join(c.get("text", "") for c in e.get("content", []) if isinstance(c, dict)).strip()


def main(sid, founders):
    threads = all_pages(f"/sessions/{sid}/threads?limit=100")
    events = all_pages(f"/sessions/{sid}/events?limit=500")
    by_agent = {}
    for t in threads:
        by_agent.setdefault(t["agent"]["name"].removeprefix(P), []).append(t)
    tid_agent = {t["id"]: t["agent"]["name"].removeprefix(P) for t in threads}
    created = lambda name: min((t["created_at"] for t in by_agent.get(name, [])), default=None)

    checks = []
    add = lambda name, ok, detail, hard=True: checks.append({"check": name, "pass": bool(ok), "detail": detail, "hard": hard})

    # 1. one discovery thread and one founder thread per named founder
    for f in founders:
        n = len(by_agent.get(f"founder-{f}", []))
        add(f"one thread for founder-{f}", n == 1, f"{n} threads (extra threads mean a message went to the agent instead of its recorded thread)")
    nd = len(by_agent.get("discovery-agent", []))
    add("one discovery call per founder", nd == len(founders), f"{nd} discovery threads for {len(founders)} founders")

    # 2. every specialist dispatched, in the right order
    for a in ["linear-scout", "notion-scout", "miner", "data-analyst"]:
        add(f"{a} dispatched", a in by_agent, f"{len(by_agent.get(a, []))} threads")
    scouts = [created(a) for a in ("linear-scout", "notion-scout") if created(a)]
    if created("miner") and scouts:
        add("miner started after scouts", created("miner") > max(scouts), f"miner {created('miner')} vs scouts {max(scouts)}")
    if created("miner") and created("data-analyst"):
        add("data-analyst started after miner", created("data-analyst") > created("miner"), "")
    expected = {"chief-of-staff", "discovery-agent", "linear-scout", "notion-scout", "miner", "data-analyst"} | {f"founder-{f}" for f in founders}
    extra = sorted(set(by_agent) - expected)
    add("no unexpected agents called", not extra, f"unexpected: {extra}" if extra else "none")

    # 3. relay fidelity, from the coordinator's primary-thread message events
    received = [(e.get("from_session_thread_id"), text(e)) for e in events if e["type"] == "agent.thread_message_received"]
    sent = [(e.get("to_session_thread_id") or e.get("session_thread_id_to") or e.get("target_session_thread_id"), text(e))
            for e in events if e["type"] == "agent.thread_message_sent"]
    from_discovery = {m for tid, m in received if tid_agent.get(tid) == "discovery-agent"}
    from_founders = {m for tid, m in received if tid_agent.get(tid, "").startswith("founder-")}
    q_to_founders = [(tid, m) for tid, m in sent if tid_agent.get(tid, "").startswith("founder-")]
    a_to_discovery = [m.removeprefix("FOUNDER:").strip() for tid, m in sent
                      if tid_agent.get(tid) == "discovery-agent" and m.startswith("FOUNDER:")]
    if q_to_founders:
        exact_q = sum(m in from_discovery for _, m in q_to_founders)
        add("questions relayed verbatim", exact_q == len(q_to_founders), f"{exact_q}/{len(q_to_founders)} exact")
        per_founder = {}
        for tid, _ in q_to_founders:
            per_founder[tid_agent[tid]] = per_founder.get(tid_agent[tid], 0) + 1
        over = {k: v for k, v in per_founder.items() if v > 8}
        add("at most 8 questions per call", not over, json.dumps(per_founder))
    else:
        add("questions relayed verbatim", False, "no sent-to-founder events found; check the event field for the target thread", hard=False)
    if a_to_discovery:
        exact_a = sum(m in from_founders for m in a_to_discovery)
        add("answers relayed verbatim", exact_a == len(a_to_discovery), f"{exact_a}/{len(a_to_discovery)} exact")

    # 4. manifest says every step done, and each delegate really ran
    mf = ROOT / "runs" / sid / "run-manifest.json"
    if mf.exists():
        m = json.loads(mf.read_text())
        steps = m if isinstance(m, list) else m.get("steps", [])
        not_done = [s.get("step") for s in steps if s.get("status") != "done"]
        add("manifest: every step done", steps and not not_done, f"{len(steps)} steps, not done: {not_done}")
        claimed = {d.removeprefix(P) for s in steps for d in s.get("delegated_to", [])}
        ghost = sorted(c for c in claimed if c not in by_agent and not c.startswith("founder") and c != "chief-of-staff")
        add("manifest matches trace", not ghost, f"claimed but never ran: {ghost}" if ghost else "consistent")
    else:
        add("manifest present", False, "run-manifest.json not downloaded (./launch.sh outputs first)")

    ok = all(c["pass"] for c in checks if c["hard"])
    out = ROOT / "runs" / sid
    out.mkdir(parents=True, exist_ok=True)
    (out / "trace-eval.json").write_text(json.dumps({"pass": ok, "checks": checks, "threads": len(threads)}, indent=2))
    print(f"\n  🧪 trace eval {'PASS' if ok else 'FAIL'}  ({len(threads)} threads)")
    for c in checks:
        print(f"   {'✅' if c['pass'] else ('❌' if c['hard'] else '⚠️ ')} {c['check']:34} {c['detail']}")
    print()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or ["priya", "tomas", "aisha", "ben"])
