#!/usr/bin/env python3
"""Render dashboard.html from data/metrics.json only (standard library, self-contained output)."""
import json, os, html

OUT = os.environ.get("ROOM_OUT", "/mnt/session/outputs")
M = json.load(open(os.path.join(OUT, "data", "metrics.json"), encoding="utf-8"))
E = lambda s: html.escape(str(s), quote=True)
H = M["headline"]


def bar_chart(rows, title, max_value=None, unit="", W=680):
    """rows: list of (label, detail, value, tag). Horizontal bars, label line above each bar,
    short value at the bar end. Returns inline SVG."""
    left, right = 4, 44
    row_h = 44
    h = row_h * len(rows) + 8
    mx = max_value or max([r[2] for r in rows] + [1])
    parts = [f'<svg class="chart" viewBox="0 0 {W} {h}" width="100%" role="img" aria-label="{E(title)}">'
             f'<title>{E(title)}</title>']
    for i, (label, detail, v, tag) in enumerate(rows):
        y = 6 + i * row_h
        bw = max(2, (W - left - right) * v / mx)
        tag_s = f' <tspan class="tag">{E(tag)}</tspan>' if tag else ""
        det = f' <tspan class="muted">{E(detail)}</tspan>' if detail else ""
        parts.append(f'<text x="{left}" y="{y + 12}" class="lbl">{E(label)}{tag_s}{det}</text>')
        parts.append(f'<rect x="{left}" y="{y + 18}" width="{bw:.1f}" height="16" rx="3" class="bar"/>')
        parts.append(f'<text x="{left + bw + 6:.1f}" y="{y + 31}" class="val">{E(v)}{E(unit)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def card(value, label, sub=""):
    return (f'<div class="card"><div class="big">{E(value)}</div><div class="cl">{E(label)}</div>'
            f'{f"<div class=muted>{E(sub)}</div>" if sub else ""}</div>')


def mark(ok):
    return '<span class="ok">✓</span>' if ok else '<span class="bad">✗</span>'


# ------------------------------------------------------------------ headline
sc = M["cluster_status_vs_last_run"]["counts"]
ac = M["agent_check"]["summary"]
cov = M["coverage"]
ver = M["verification"]
cards = "".join([
    card(H["distinct_founders"], "distinct founders", f'{H["new_founders_this_run"]} new ({", ".join(H["new_founder_names"])}); '
         f'{H["founders_evidenced_this_run"]} evidenced this run'),
    card(H["clusters_total"], "pain clusters", f'{H["blocker_clusters"]} blockers + {H["requirement_clusters"]} requirement'),
    card(f'{sc["new"]} / {sc["growing"]} / {sc["unchanged"]}', "new / growing / unchanged", "vs last run (pain library)"),
    card(H["evidence_items_this_run"], "evidence items this run",
         " · ".join(f"{k} {v}" for k, v in M["evidence_items_per_source"].items())),
    card(f'{H["agent_steps_passed"]}/{H["agent_steps_checked"]}', "agent steps passed",
         f'{H["stray_threads"]} stray threads'),
    card(H["run_cost"], "run cost", "no telemetry in this session"),
    card(f'{H["cluster_quotes_verbatim"]}/{H["cluster_quotes"]}', "cluster quotes verbatim",
         f'report: {H["report_quotes_verbatim"]}/{H["report_quotes"]}'),
    card(H["founders_paused_or_stopped"], "founders paused or stopped", ", ".join(H["founders_paused_or_stopped_names"])),
])

# ------------------------------------------------------------------ top 3 fixes
dod = M.get("founder_definition_of_done")
dod_html = (f'<blockquote class="dod">“{E(dod["quote"])}” <cite>{E(dod["author"])}, {E(dod["link"])}</cite></blockquote>'
            if dod else "")
fixes = []
for t in M["top3_fixes"]:
    qs = "".join(f'<li><q>{E(q["quote"])}</q> <span class="src">{E(q["author"])} · {E(q["source"])} · {E(q["link"])}</span></li>'
                 for q in t["quotes"])
    fixes.append(f'''<div class="fix"><div class="fixhead"><span class="rank">#{E(t["rank"])}</span>
<span class="fixfor">{E(" + ".join(t["fix_for"]))}</span>
<span class="pill">{E(t["founders_served"])} founders: {E(", ".join(t["founder_names"]))}</span></div>
<p>{E(t["fix"])}</p><ul class="quotes">{qs}</ul></div>''')

# ------------------------------------------------------------------ agent check
steps_rows = []
for a in M["agent_check"]["steps"]:
    files = "<br>".join(f'{mark(f["exists"] and f["bytes"] > 0)} <code>{E(f["path"])}</code> <span class="muted">{E(f["bytes"])} B</span>'
                        for f in a["expected_outputs"]) or '<span class="muted">none listed</span>'
    claims = "<br>".join(f'{mark(c["ok"])} {E(c["claim"])} <span class="muted">→ {E(c["observed"])}</span>'
                         for c in a["claims"]) or f'<span class="muted">{E(a["note"])}</span>'
    v = a["verdict"]
    vcls = "pass" if v == "pass" else ("fail" if v == "fail" else "self")
    thr = "<br>".join(f'<code class="tid">{E(t)}</code>' for t in a["thread_ids"]) or "not recorded"
    steps_rows.append(f'<tr><td>{E(a["step"])}</td><td><b>{E(a["agent"])}</b><br><span class="muted">{E(a["task"])}</span><div class="muted">thread: {thr}</div></td>'
                      f'<td>{files}<div class="muted">{E(a["files_present"])}/{E(a["files_expected"])} present</div></td>'
                      f'<td>{claims}</td><td><span class="verdict {vcls}">{E(v)}</span></td>'
                      f'<td class="muted">{E(a["cost"])}</td></tr>')
def thread_cell(t):
    return "<code>" + E(t["thread_id"]) + "</code>" if t["thread_id"] else E(t["detail"])


thread_rows = "".join(
    f'<tr><td>{E(t["founder"])}</td><td>{E(t["role"])}</td><td>{thread_cell(t)}</td>'
    f'<td>{E(t["step"]) if t["step"] is not None else "–"}</td>'
    f'<td class="{"bad" if t["status"].startswith("STRAY") else ""}">{E(t["status"])}</td><td class="muted">{E(t["cost"])}</td></tr>'
    for t in M["agent_check"]["threads"])
spec = M["cost"]["spec"]
spec_fields = "".join(f"<li><code>{E(k)}</code>: {E(v)}</li>" for k, v in spec["fields_per_thread"].items())
spec_derived = "".join(f"<li><code>{E(k)}</code>: {E(v)}</li>" for k, v in spec["derived_metrics"].items())

# ------------------------------------------------------------------ charts
tc = M["top_clusters_by_founders"]
cl_rows = [(f'{c["rank"]}. {c["id"]}', f'{", ".join(c["founder_names"])} · {", ".join(c["sources"])}',
            c["founders"], c["status"] if c["status"] != "unchanged" else ("requirement" if c["kind"] == "requirement" else ""))
           for c in tc]
cl_chart = bar_chart(cl_rows, "Clusters ranked by distinct founders")
pr = M["pains_by_primitive"]["rows"]
pr_chart = bar_chart([(r["primitive"], f'{", ".join(r["founder_names"])} · {r["blocker_clusters"]} cluster{"s" if r["blocker_clusters"] != 1 else ""}', r["founders"], "")
                      for r in pr], "Distinct founders blocked, by CMA primitive")
ev = M["evidence_items_per_source"]
ps = M["pains_by_source"]
src_keys = list(ev.keys())
ev_chart = bar_chart([(k, "", ev[k], "") for k in src_keys], "Evidence items per source, this run", W=360)
fo_chart = bar_chart([(k, "", ps["founders_by_source"].get(k, 0), "") for k in src_keys], "Founders by source (cumulative)", W=360)
bc_chart = bar_chart([(k, "", ps["blocker_clusters_citing_source"].get(k, 0), "") for k in src_keys],
                     "Blocker clusters citing each source", W=360)
qs_chart = bar_chart([(k, "", ps["cluster_quotes_by_source"].get(k, 0), "") for k in src_keys], "Cluster quotes by source", W=360)
files_list = "".join(f"<li><code>{E(k)}</code>: {E(v)}</li>" for k, v in M["evidence_items_per_file"].items())

# ------------------------------------------------------------------ coverage / quality
zero = cov["sources_with_zero_items"]
unc = "".join(f'<li><code>{E(u["id"])}</code>: {E(u["note"])}</li>' for u in cov["evidence_items_unclustered"])
dq = "".join(f"<li>{E(x)}</li>" for x in M["data_quality"])
mism = ver["mismatches"]
mism_html = ("<ul>" + "".join(f'<li class="bad">{E(x["check"])}: {E(x["detail"])}</li>' for x in mism) + "</ul>") if mism \
    else '<p><span class="ok">✓</span> No mismatches.</p>'
status_new = ", ".join(M["cluster_status_vs_last_run"]["new"])
status_grow = ", ".join(f'{g["id"]} (now {g["founders"]}; added {", ".join(g["added"])})' for g in M["cluster_status_vs_last_run"]["growing"])
carried = ", ".join(M["cluster_status_vs_last_run"]["unchanged_carried_without_evidence"])

CSS = """
:root{--bg:#ffffff;--fg:#1c1917;--muted:#6b6560;--line:#e7e2dc;--panel:#faf8f5;--accent:#c2410c;--accent-soft:#fdebe1;--ok:#15803d;--bad:#b91c1c}
@media (prefers-color-scheme: dark){:root{--bg:#161412;--fg:#f1ede8;--muted:#a8a09a;--line:#34302c;--panel:#1f1c19;--accent:#fb923c;--accent-soft:#3a2416;--ok:#4ade80;--bad:#f87171}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:1080px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:36px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--accent)}
h3{font-size:15px;margin:18px 0 6px}
.muted{color:var(--muted);font-size:13px}
.cards{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}
.card{flex:1 1 220px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.big{font-size:28px;font-weight:700;color:var(--accent);line-height:1.1}
.cl{font-weight:600;margin-top:2px}
.fix{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:8px;padding:12px 16px;margin:12px 0}
.fixhead{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.rank{font-size:22px;font-weight:800;color:var(--accent)}
.fixfor{font-weight:700}
.pill,.tagpill{background:var(--accent-soft);color:var(--fg);border-radius:999px;padding:2px 10px;font-size:13px}
.quotes{margin:6px 0 0;padding-left:18px}.quotes li{margin:4px 0}
q{font-style:italic}.src{color:var(--muted);font-size:12px;display:block}
blockquote.dod{margin:8px 0 4px;padding:8px 14px;border-left:3px solid var(--accent);background:var(--panel);font-style:italic}
blockquote.dod cite{display:block;font-style:normal;color:var(--muted);font-size:12px}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:8px 0}
th,td{border-bottom:1px solid var(--line);padding:7px 8px;text-align:left;vertical-align:top}
th{background:var(--panel);font-weight:600}
code{font:12px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;overflow-wrap:break-word;word-wrap:break-word}
table.agents td:nth-child(3) code{white-space:nowrap}
code.tid{word-break:break-all}
.ok{color:var(--ok);font-weight:700}.bad{color:var(--bad);font-weight:700}
.verdict{border-radius:6px;padding:2px 8px;font-weight:700;font-size:12.5px;white-space:nowrap}
.verdict.pass{color:var(--ok);border:1px solid var(--ok)}.verdict.fail{color:var(--bad);border:1px solid var(--bad)}
.verdict.self{color:var(--muted);border:1px dashed var(--muted)}
.chart{display:block;max-width:760px}
.chart .lbl{font-size:13px;fill:var(--fg);font-weight:600}
.chart .muted{font-size:12px;fill:var(--muted);font-weight:400}
.chart .tag{font-size:12px;fill:var(--accent);font-weight:700}
.chart .val{font-size:13px;fill:var(--fg);font-weight:700}
.chart .bar{fill:var(--accent)}
.row{display:flex;flex-wrap:wrap;gap:24px}.col{flex:1 1 400px;min-width:280px}
.src4 .col{flex:1 1 440px}
.src4 .chart{max-width:380px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin:8px 0}
ul.tight li{margin:3px 0}
footer{margin-top:40px;color:var(--muted);font-size:12px}
"""

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Room Miner: {E(M["run"])}</title><style>{CSS}</style></head>
<body><main>
<h1>Room Miner: where founders get stuck</h1>
<div class="muted">Run <code>{E(M["run"])}</code> · mode {E(M["mode"])} · founder {E(M["founder"])} · compared with <code>{E(M["previous_run"])}</code> · built {E(M["generated_at"])} from <code>data/metrics.json</code></div>

<section><h2>Headline numbers</h2><div class="cards">{cards}</div></section>

<section><h2>Monday list: top {E(len(M["top3_fixes"]))} fixes</h2>
<div class="muted">Ranked by distinct founders each fix would unblock (from clusters.json). Every quote is verbatim from the evidence files.</div>
{dod_html}
{"".join(fixes)}
</section>

<section><h2>Did each agent do its job?</h2>
<p class="muted">For each specialist step in <code>run-manifest.json</code>: the expected outputs are compared with the files on disk, and the numeric claims in the step notes are compared with the file contents. A step passes only if every file exists, is non-empty, and every claim holds.
<b>{E(ac["passed"])}/{E(ac["steps_checked"])} specialist steps pass</b>, {E(ac["failed"])} fail. Step {E(", ".join(map(str, ac["self_check_steps"])))} (this data-analyst step) is a self-check and is not counted.</p>
<table class="agents"><colgroup><col style="width:4%"><col style="width:25%"><col style="width:27%"><col style="width:30%"><col style="width:8%"><col style="width:6%"></colgroup><thead><tr><th>Step</th><th>Agent / task</th><th>Expected outputs vs disk</th><th>Claims checked</th><th>Verdict</th><th>Cost</th></tr></thead>
<tbody>{"".join(steps_rows)}</tbody></table>
<h3>Agent threads (from <code>work/threads.json</code>): {E(ac["agent_threads_recorded"])} recorded, <span class="{"bad" if ac["stray_threads"] else "ok"}">{E(ac["stray_threads"])} stray / wasted</span></h3>
<table><thead><tr><th>Founder</th><th>Role</th><th>Thread</th><th>Manifest step</th><th>Status</th><th>Cost</th></tr></thead><tbody>{thread_rows}</tbody></table>
<p class="muted">Steps without a recorded thread id: {E(", ".join(map(str, ac["steps_without_recorded_thread"])) or "none")}. A thread missing from threads.json can't be checked for waste.</p>
<div class="panel"><b>Cost: {E(M["cost"]["display"])}.</b> {E(spec["reason"])}<br>
<span class="muted">Once telemetry exists, this check will capture the following per <b>{E(spec["unit_of_analysis"])}</b>, sourced from {E(spec["source"])}:</span>
<div class="row"><div class="col"><h3>Per-thread fields</h3><ul class="tight muted">{spec_fields}</ul></div>
<div class="col"><h3>Derived metrics</h3><ul class="tight muted">{spec_derived}</ul></div></div>
<span class="muted">Ready when: {E(spec["ready_when"])}.</span></div>
</section>

<section><h2>Top clusters by founders</h2>
<div class="muted">Distinct founders per cluster (cumulative, from the pain library). Tags mark status vs last run. New: {E(status_new)}. Growing: {E(status_grow)}. Carried with no evidence this run: {E(carried)}.</div>
{cl_chart}
</section>

<section><h2>Blockers by CMA primitive</h2>
<div class="muted">{E(M["pains_by_primitive"]["method"])}</div>
{pr_chart}
</section>

<section><h2>Source mix</h2>
<div class="row src4">
<div class="col"><h3>Evidence items per source (this run)</h3>{ev_chart}<ul class="tight muted">{files_list}</ul></div>
<div class="col"><h3>Founders by source (cumulative)</h3>{fo_chart}</div>
<div class="col"><h3>Blocker clusters citing each source</h3>{bc_chart}</div>
<div class="col"><h3>Cluster quotes by source</h3>{qs_chart}</div>
</div></section>

<section><h2>Coverage and data quality</h2>
<div class="row"><div class="col"><h3>Coverage</h3><ul class="tight">
<li>Founders with a needs brief: <b>{E(cov["founders_with_brief"])}/{E(cov["founders_total"])}</b> ({E(", ".join(cov["founders_with_brief_names"]))}). Founders called this run with a brief: {E(cov["founders_called_this_run_with_brief"])}/{E(cov["founders_called_this_run"])}.</li>
<li>Founders counted from the pain library only (no evidence in this run): {E(", ".join(cov["founders_counted_from_library_only"]))}.</li>
<li>Sources returning zero items: <b>{E(", ".join(zero) if zero else "none")}</b> (expected: {E(", ".join(cov["sources_expected"]))}).</li>
<li>Clusters with no evidence this run: {E(", ".join(cov["clusters_with_no_evidence_this_run"]))}.</li>
<li>Evidence items clustered: {E(cov["evidence_items_clustered"])}; context only: {E(cov["evidence_items_context_only"])}; not clustered: {E(len(cov["evidence_items_unclustered"]))}.</li>
</ul><h3>Not clustered</h3><ul class="tight muted">{unc}</ul></div>
<div class="col"><h3>Verification against room-report.md, clusters.json and the pain library</h3>
<p>{E(ver["checks_passed"])}/{E(ver["checks_run"])} checks passed.</p>{mism_html}</div></div>
<h3>Data-quality notes</h3><ul class="tight">{dq}</ul>
</section>
<footer>Self-contained file: no external scripts, fonts or images. Every number on this page is read from data/metrics.json (generated by data/build.py; rendered by data/render.py).</footer>
</main></body></html>
"""
with open(os.path.join(OUT, "dashboard.html"), "w", encoding="utf-8") as fh:
    fh.write(page)
print("wrote dashboard.html", len(page), "bytes")
