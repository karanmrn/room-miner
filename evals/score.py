"""Score one finished Room Miner eval session and append a row to evals/scoreboard.csv.

    python3 evals/score.py <session_id> <case>        e.g. python3 evals/score.py sesn_... case-01

Needs the session's outputs downloaded first (./launch.sh outputs <session_id>).

Layers scored here (the Outcome is graded in-run by the platform; trace checks live in trace_eval.py):
  recall             hidden pains from answer-key.json found in room-report.md  (LLM judge, outside the session)
  fabricated quotes  quoted strings in the report and briefs that appear in no evidence item or transcript (exact match)
  relay fidelity     persona verbatim lines that reached the transcript word for word vs. altered
  cost               tokens and USD from the session's usage, split with pricing.json; cost per recalled pain

The answer key is read only here, on your machine. It never enters a session.
"""
import csv
import datetime
import json
import os
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://api.anthropic.com/v1"
JUDGE_MODEL = "claude-sonnet-5"


def load_key():
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("ANTHROPIC_API_KEY missing from .env")


KEY = load_key()


def call(method, path, body=None, beta="managed-agents-2026-04-01"):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body else None)
    req.add_header("x-api-key", KEY)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("content-type", "application/json")
    if beta:
        req.add_header("anthropic-beta", beta)
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.JSONDecoder(strict=False).decode(r.read().decode())


QUOTE = re.compile(r"[\"“]([^\"”]{15,})[\"”]")
norm = lambda s: re.sub(r"\s+", " ", s.replace("’", "'").replace("‘", "'")).strip()


def main(session_id, case):
    out = ROOT / "runs" / session_id
    report = (out / "room-report.md").read_text() if (out / "room-report.md").exists() else ""
    if not report:
        sys.exit(f"no room-report.md under {out}; run ./launch.sh outputs {session_id} first")
    key = json.loads((ROOT / "evals" / case / "answer-key.json").read_text())

    # evidence corpus: every evidence item text + every transcript
    corpus = []
    for f in (out / "evidence").glob("*.jsonl"):
        for line in f.read_text().splitlines():
            try:
                corpus.append(norm(json.loads(line).get("text", "")))
            except json.JSONDecodeError:
                pass
    transcripts = {f.stem: f.read_text() for f in (out / "calls").glob("*.md")}
    corpus += [norm(t) for t in transcripts.values()]
    blob = "\n".join(corpus)

    # fabricated quotes (exact, whitespace- and apostrophe-normalised)
    quoted = []
    for f in [out / "room-report.md", *sorted((out / "briefs").glob("*.md"))]:
        quoted += [(f.name, q) for q in QUOTE.findall(f.read_text())]
    fabricated = [(f, q) for f, q in quoted if norm(q) not in blob]

    # relay fidelity: persona verbatim lines that reached a transcript exactly vs. altered
    verbatim_total = verbatim_exact = 0
    for persona in (ROOT / "evals" / case / "personas").glob("*.md"):
        if persona.name == "TEMPLATE.md":
            continue
        t = norm(transcripts.get(persona.stem, ""))
        for line in re.findall(r'Verbatim when revealed: "(.+)"', persona.read_text()):
            head = norm(line)[:30]
            if head in t:  # the line was revealed in this call
                verbatim_total += 1
                verbatim_exact += norm(line) in t

    # recall: LLM judge, answer key outside the session
    pains = "\n".join(f"{p['id']}: {p['pain']}" for p in key["pains"])
    judge = call("POST", "/messages", beta=None, body={
        "model": JUDGE_MODEL, "max_tokens": 2000,
        "messages": [{"role": "user", "content":
            "You grade recall. For each hidden pain below, decide whether the REPORT surfaces the same "
            "underlying pain (same root problem, any wording), with at least one supporting quote.\n\n"
            f"HIDDEN PAINS:\n{pains}\n\nREPORT:\n{report}\n\n"
            'Reply with JSON only: {"P01": {"found": true, "cluster": "<report cluster name or null>"}, ...}'}]})
    text = judge["content"][0]["text"]
    verdicts = json.loads(text[text.find("{"): text.rfind("}") + 1])
    found = [pid for pid, v in verdicts.items() if v.get("found")]
    recall = len(found) / len(key["pains"])

    # cost
    s = call("GET", f"/sessions/{session_id}")
    u = s.get("usage") or {}
    prices = json.loads((ROOT / "pricing.json").read_text())
    model = next(l.split("=", 1)[1] for l in (ROOT / "IDS.env").read_text().splitlines() if l.startswith("MODEL="))
    p = prices["usd_per_mtok"][model]
    cw = u.get("cache_creation_input_tokens", 0)
    if isinstance(u.get("cache_creation"), dict):
        cw = sum(v for v in u["cache_creation"].values() if isinstance(v, (int, float)))
    tin, tout, tcr = u.get("input_tokens", 0), u.get("output_tokens", 0), u.get("cache_read_input_tokens", 0)
    secs = u.get("active_seconds") or 0
    est = (tin * p["input"] + cw * p["cache_write_5m"] + tcr * p["cache_read"] + tout * p["output"]) / 1e6 \
        + secs / 3600 * prices["session_runtime_usd_per_hour"]
    lc = u.get("list_cost") or s.get("list_cost")
    cost = est
    if isinstance(lc, dict) and "amount" in lc:
        cost = int(lc["amount"]) / 100  # whole cents -> USD; authoritative when present
    outcome = ",".join(e.get("result", "?") for e in s.get("outcome_evaluations") or []) or "none"

    trace_file = out / "trace-eval.json"
    trace_pass = json.loads(trace_file.read_text()).get("pass") if trace_file.exists() else ""

    row = {
        "run_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "case": case, "session": session_id,
        "agent_version": next((l.split("=", 1)[1] for l in (ROOT / "IDS.env").read_text().splitlines()
                               if l.startswith("CHIEF_OF_STAFF_VERSION=")), ""),
        "outcome": outcome, "trace_pass": trace_pass,
        "recall": round(recall, 3), "fabricated_quotes": len(fabricated),
        "relay_exact": f"{verbatim_exact}/{verbatim_total}",
        "tokens_in": tin + cw + tcr, "tokens_out": tout, "cost_usd": round(cost, 3), "active_s": round(secs),
        "cost_per_recalled_pain": round(cost / len(found), 3) if found else "",
    }
    sb = ROOT / "evals" / "scoreboard.csv"
    new = not sb.exists()
    with sb.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)

    (out / "score.json").write_text(json.dumps({**row, "verdicts": verdicts, "fabricated": fabricated}, indent=2))
    bar = key["pass_bar"]
    ok = recall >= bar["recall_min"] and len(fabricated) <= bar["fabricated_quotes_max"]
    print(f"\n  🧪 {case}  {'PASS' if ok else 'FAIL'}   recall {recall:.0%} ({len(found)}/{len(key['pains'])})"
          f"   fabricated quotes {len(fabricated)}   relay exact {verbatim_exact}/{verbatim_total}")
    print(f"  🎯 outcome {outcome}   💵 ${cost:.2f}   per recalled pain ${row['cost_per_recalled_pain']}")
    missed = [p for p in key["pains"] if p["id"] not in found]
    if missed:
        print("  missed: " + "; ".join(f"{p['id']} {p['pain']}" for p in missed))
    for f, q in fabricated[:5]:
        print(f"  ✗ not in evidence ({f}): \"{q[:90]}\"")
    print()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
