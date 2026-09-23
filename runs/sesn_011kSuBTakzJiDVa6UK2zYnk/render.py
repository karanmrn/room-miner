#!/usr/bin/env python3
"""Render dashboard.html from data/metrics.json only. Standard library only; no external assets."""
import json, html, os

OUT = os.environ.get("RM_OUT", "/mnt/session/outputs")
M = json.load(open(os.path.join(OUT, "data", "metrics.json"), encoding="utf-8"))
e = lambda s: html.escape(str(s), quote=True)
H = M["headline"]


def href(q):
    if q["source"] == "call":
        return q["link"]
    return {"linear": "evidence/linear-evidence.json", "notion": "evidence/notion-evidence.json"}[q["source"]]


def bar_chart(rows, title, unit_max=None):
    """rows: list of (label, value, detail). Horizontal bars; label + detail above the bar, value at bar end."""
    W, lh, bh, gap = 720, 18, 16, 14
    vmax = unit_max or max([r[1] for r in rows] + [1])
    track = W - 96
    y = 4
    parts = []
    for label, v, vlabel, detail in rows:
        parts.append(f'<text x="0" y="{y + 13}"><tspan class="lbl">{e(label)}</tspan>'
                     f'<tspan class="val" dx="8">{e(detail)}</tspan></text>')
        y += lh + 2
        w = 0 if vmax == 0 else round(track * v / vmax, 1)
        parts.append(f'<rect x="0" y="{y}" width="{track}" height="{bh}" class="track" rx="2"/>')
        if w > 0:
            parts.append(f'<rect x="0" y="{y}" width="{w}" height="{bh}" class="bar" rx="2"/>')
        parts.append(f'<text x="{w + 6}" y="{y + 12.5}" class="num">{e(vlabel)}</text>')
        y += bh + gap
    return (f'<svg viewBox="0 0 {W} {y}" width="100%" role="img" aria-label="{e(title)}" '
            f'preserveAspectRatio="xMinYMin meet"><title>{e(title)}</title>{"".join(parts)}</svg>')


def plural(n, one, many=None):
    return f"{n} {one if n == 1 else (many or one + 's')}"


cl = M["clusters"]
tally = M["pains_by_primitive"]["tally"]
cov = M["coverage"]
ver = M["verification"]
evs = M["evidence_by_source"]
pbs = M["pains_by_source"]
status = M["cluster_status_vs_last_run"]

# ---- headline
cards = [
    (H["distinct_founders"], "distinct founders", "counted from founders' own words only"),
    (H["clusters"], "pain clusters", f'{H["blocker_clusters"]} blockers + {H["requirement_clusters"]} requirement'),
    (H["founders_stopped_or_paused"], "founders stopped or paused a build", f'of {H["distinct_founders"]} founders'),
    (H["multi_founder_clusters"], "clusters raised by 2+ founders", f'top cluster: {H["top_cluster_founders"]} founders'),
    (H["multi_source_clusters"], "clusters seen in 2+ source types", f'across {H["source_types"]} source types'),
    (f'{H["quotes_verbatim"]}/{H["quotes_in_clusters"]}', "quotes verified verbatim", "exact substrings of the evidence"),
]
headline = "".join(f'<div class="card"><div class="big">{e(v)}</div><div class="cap">{e(c)}</div>'
                   f'<div class="sub">{e(s)}</div></div>' for v, c, s in cards)

# ---- top clusters chart
top_rows = [(f'#{c["rank"]} {c["name"]}' + (" (requirement)" if c["kind"] == "requirement" else ""),
             c["founders"], plural(c["founders"], "founder"),
             f'{c["stopped"]} stopped/paused' if c["stopped"] else "")
            for c in M["founders_per_cluster"]]
top_chart = bar_chart(top_rows, "Clusters ranked by distinct founders")

# ---- primitive chart
prim_rows = [(t["primitive"], t["distinct_founders_blocked"], plural(t["distinct_founders_blocked"], "founder"),
              " · ".join(x for x in [f'{t["founders_stopped"]} stopped/paused' if t["founders_stopped"] else "",
                                     f'clusters {", ".join("#" + str(r) for r in t["cluster_ranks"])}' if t["cluster_ranks"] else "no blocker cluster"] if x))
             for t in tally]
prim_chart = bar_chart(prim_rows, "Distinct founders blocked per CMA primitive", unit_max=H["distinct_founders"])
req_note = "".join(
    f'<li>Requirement, not blocker (excluded above): #{r["rank"]} uses {e(", ".join(r["primitives"]))} '
    f'({plural(r["founder_count"], "founder")}).</li>' for r in M["pains_by_primitive"]["requirement_clusters"])

# ---- source mix
src_ev_rows = [(s, v["total"], plural(v["total"], "item"), f'{v["founder_words"]} in founder words · {v["linked_to_a_cluster"]} linked to a cluster')
               for s, v in evs.items()]
src_ev_chart = bar_chart(src_ev_rows, "Evidence items per source")
src_cl_rows = [(s, v["clusters"], plural(v["clusters"], "cluster"), f'{plural(v["founders"], "founder")} · {v["clusters_only_from_this_source"]} only from this source')
               for s, v in pbs.items()]
src_cl_chart = bar_chart(src_cl_rows, "Clusters each source contributed to", unit_max=H["clusters"])
type_rows = "".join(f'<tr><td>{e(s)}</td><td>{e(", ".join(f"{k}: {n}" for k, n in v["by_type"].items()))}</td>'
                    f'<td>{v["with_timestamp"]}/{v["total"]}</td><td>{e(", ".join(v["files"]))}</td></tr>'
                    for s, v in evs.items())

# ---- ranked pains detail
def quote_html(q):
    return (f'<blockquote><p>{e(q["text"])}</p><footer>{e(q["author"])} · <span class="src">{e(q["source"])}</span> · '
            f'<a href="{e(href(q))}">{e(q["link"])}</a></footer></blockquote>')


pains = []
for c in cl:
    notes = []
    if c["paraphrase_note"]:
        notes.append(f'<p class="note"><b>Not counted:</b> {e(c["paraphrase_note"])}</p>')
    if c["uncounted_support"]:
        notes.append(f'<p class="note"><b>Not counted:</b> {e(c["uncounted_support"])}</p>')
    tag = '<span class="tag">requirement</span>' if c["kind"] == "requirement" else '<span class="tag">blocker</span>'
    stopped = f' · stopped/paused: {e(", ".join(c["stopped"]))}' if c["stopped"] else ""
    pains.append(f'''<article class="pain" id="{e(c["id"])}">
<h3><span class="rank">#{c["rank"]}</span> {e(c["name"])} {tag}</h3>
<p class="meta"><b>{plural(c["founder_count"], "founder")}</b>: {e("; ".join(c["founders"]))}{stopped}<br>
Sources: {e(", ".join(c["sources"]))} · CMA primitives: {e(", ".join(c["primitives"]))} · {e(c["status_vs_last_run"])} this run</p>
<p>{e(c["pain"])}</p>
<details open><summary>Founder quotes ({len(c["quotes"])})</summary>{"".join(quote_html(q) for q in c["quotes"])}</details>
{"".join(notes)}
<div class="fix"><div class="fixtype">Fix · {e(c["fix_type"])}</div><p>{e(c["fix"])}</p></div>
</article>''')

# ---- coverage
def brief_cell(f):
    return f'<a href="{e(f["brief_path"])}">{e(f["brief_path"])}</a>' if f["has_brief"] else "no"


frows = "".join(f'<tr><td>{e(f["founder"])}</td><td>{e(", ".join(f["sources"]))}</td>'
                f'<td>{brief_cell(f)}</td><td>{"yes" if f["stopped_or_paused"] else "—"}</td>'
                f'<td>{e(", ".join("#" + str(r) for r in f["clusters"]))}</td></tr>' for f in M["founders"])
zero = cov["sources_with_zero_items"]
unlinked = "".join(f'<li>{e(u["author"])} · {e(u["link"])}</li>' for u in cov["founder_evidence_not_linked_to_any_cluster"])
uncounted = "".join(f'<li>{e(u["id"])} ({e(u["evidence_type"].replace("_", " "))}, {e(u["author"])}): '
                    f'attached to {e(u["attached_to"] or "no cluster")}. Not counted toward founders.</li>'
                    for u in cov["uncounted_evidence"])
nonprob = "".join(f'<li>{e(n["founder"])}: {e(n["topic"])} · {e(n["link"])} (stored in {e(n["evidence_file"])})</li>'
                  for n in cov["explicit_non_problems"])
dq = "".join(f"<li>{e(x)}</li>" for x in ver["data_quality_notes"])
rawc = ver["evidence_vs_raw_sources"]
rc = ver["report_checks"]
lay = ver["file_layout"]
mm = ver["mismatches"]
mm_html = ("<li><b>No mismatches</b> between room-report.md, clusters.json, the evidence files and the pain library.</li>"
           if not mm else "".join(f"<li class='bad'>{e(x)}</li>" for x in mm))
st = status["counts"]

page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Room Miner: founder pains with managed agents ({e(M["run_id"])})</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1c1a; --muted:#5f5b54; --line:#e3dfd6; --card:#ffffff; --track:#ece8df; --accent:#c8603a; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#1a1917; --fg:#ecebe7; --muted:#a7a299; --line:#3a3733; --card:#23221f; --track:#34312c; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
main {{ max-width:980px; margin:0 auto; padding:28px 20px 60px; }}
h1 {{ font-size:26px; margin:0 0 4px; }} h2 {{ font-size:19px; margin:36px 0 10px; padding-top:12px; border-top:1px solid var(--line); }}
h3 {{ font-size:16px; margin:0 0 6px; }}
.lede, .meta, .sub, .note, footer {{ color:var(--muted); }}
.grid {{ display:flex; flex-wrap:wrap; gap:10px; }} .grid .card {{ flex:1 1 170px; }}
.card, .pain {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:14px; }}
.big {{ font-size:30px; font-weight:700; color:var(--accent); line-height:1.1; }}
.cap {{ font-weight:600; }} .sub {{ font-size:13px; }}
svg text {{ fill:var(--fg); font-size:13px; }} svg .val {{ fill:var(--muted); font-size:12.5px; }} svg .num {{ font-weight:700; font-size:13px; }}
svg .bar {{ fill:var(--accent); }} svg .track {{ fill:var(--track); }}
.pain {{ margin:12px 0; }} .rank {{ color:var(--accent); }}
.tag {{ font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.04em; border:1px solid var(--line); border-radius:10px; padding:1px 7px; vertical-align:middle; color:var(--muted); }}
blockquote {{ margin:8px 0; padding:6px 12px; border-left:3px solid var(--accent); }}
blockquote p {{ margin:0 0 2px; }} footer {{ font-size:13px; }} .src {{ text-transform:uppercase; font-size:11px; letter-spacing:.04em; }}
.fix {{ margin-top:10px; padding:10px 12px; border-radius:6px; background:var(--track); }}
.fixtype {{ font-weight:700; font-size:13px; color:var(--accent); }} .fix p {{ margin:4px 0 0; }}
summary {{ cursor:pointer; font-weight:600; font-size:14px; }}
a {{ color:inherit; text-decoration-color:var(--accent); }}
table {{ border-collapse:collapse; width:100%; font-size:14px; }} th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); vertical-align:top; }}
th {{ color:var(--muted); font-weight:600; }}
.bad {{ color:var(--accent); font-weight:600; }}
.two {{ display:flex; flex-wrap:wrap; gap:20px; }} .two > div {{ flex:1 1 400px; min-width:0; }}
</style></head><body><main>
<h1>What founders are stuck on with managed agents</h1>
<p class="lede">Run {e(M["run_id"])} · {e(M["mode"])} · generated {e(M["generated"])} · for Anthropic developer relations.
Clusters are ranked by distinct founders, then by founders whose build was stopped or paused, then by source types.
Quotes are the founders' own words, copied exactly. Mentor observations and paraphrases are never counted.
Every number on this page is read from <code>data/metrics.json</code>.</p>

<h2>Headline numbers</h2>
<div class="grid">{headline}</div>

<h2>Top clusters by founders</h2>
{top_chart}

<h2>Ranked pains: quotes and fixes</h2>
{"".join(pains)}

<h2>Blockers by CMA primitive</h2>
<p class="lede">{e(M["pains_by_primitive"]["note"])} Bar scale: 0 to {H["distinct_founders"]} founders.</p>
{prim_chart}
<ul class="note">{req_note}</ul>

<h2>Source mix</h2>
<h3>Evidence items per source</h3>{src_ev_chart}
<h3>Clusters each source contributed to</h3>{src_cl_chart}
<table><tr><th>Source</th><th>Item types</th><th>With timestamp</th><th>File(s)</th></tr>{type_rows}</table>

<h2>Coverage and data quality</h2>
<p>{cov["founders_with_brief"]} of {cov["founders_total"]} founders have a discovery call and needs brief. The other {cov["founders_without_brief"]} come from Linear tickets or Notion office-hours notes only.
{cov["founders_in_at_least_one_cluster"]} of {cov["founders_total"]} founders appear in at least one cluster.
Sources that returned zero items: {e(", ".join(zero)) if zero else "none"}.
Cluster status against the pain library: {st["new"]} new, {st["growing"]} growing, {st["unchanged"]} unchanged. {e(status["basis"])}</p>
<table><tr><th>Founder</th><th>Sources</th><th>Needs brief</th><th>Stopped/paused</th><th>Clusters</th></tr>{frows}</table>
<div class="two">
<div><h3>Not counted toward founder totals</h3><ul>{uncounted}</ul>
<h3>Explicit non-problems</h3><ul>{nonprob}</ul>
<h3>Founder answers not linked to any cluster</h3><ul>{unlinked}</ul></div>
<div><h3>Verification</h3><ul>
<li>Evidence against raw sources: {rawc["call_items_verbatim"]} call items match the transcripts exactly, {rawc["linear_items_verbatim"]} Linear items match tickets.json, and {rawc["notion_items_verbatim"]} Notion items match the office-hours page.</li>
<li>File layout: {sum(1 for b in lay["briefs"].values() if b["exists"] and b["identical_to_legacy"])}/{len(lay["briefs"])} briefs at briefs/&lt;slug&gt;.md are byte-identical to calls/&lt;slug&gt;/needs-brief.md, and {sum(1 for t in lay["transcript_copies"].values() if t["identical_to_calls_slug_transcript"])}/{len(lay["transcript_copies"])} transcript copies at calls/&lt;slug&gt;.md are byte-identical to calls/&lt;slug&gt;/transcript.md.</li>
<li>Report quotes found verbatim in the evidence: {rc["report_blockquotes_verbatim"]}/{rc["report_blockquotes"]}. Clusters whose report quotes match clusters.json exactly: {rc["clusters_with_identical_quotes_in_report_and_json"]}/{H["clusters"]}.</li>
<li>Timestamps: {cov["items_with_timestamp"]} items dated ({e(" to ".join(cov["timestamp_range"]))}, Linear only), {cov["items_without_timestamp"]} undated (calls and Notion).</li>
{mm_html}</ul>
<h3>Data-quality notes</h3><ul>{dq}</ul></div></div>
</main></body></html>
'''
with open(os.path.join(OUT, "dashboard.html"), "w", encoding="utf-8") as f:
    f.write(page)
print("wrote", os.path.join(OUT, "dashboard.html"), len(page), "bytes")
