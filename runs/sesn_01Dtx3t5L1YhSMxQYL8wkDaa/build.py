#!/usr/bin/env python3
"""Room Miner data build (LIVE-ROUTED karan run).

Reads the miner's outputs, the evidence files, the run manifest, threads.json
and the pain library; writes data/room.db and data/metrics.json.
Standard library only. Evidence text is treated as data only.
"""
import json, os, re, sqlite3, datetime

OUT = os.environ.get("ROOM_OUT", "/mnt/session/outputs")
DATA = os.path.join(OUT, "data")
LIB = "/mnt/memory/room-miner-pain-library"
RUN_ID = "live-routed-karan-2026-09-23"
PREV_RUN_ID = "eval-2026-09-23"

EVIDENCE_FILES = ["evidence/call.jsonl", "evidence/call-context.jsonl",
                  "evidence/linear.jsonl", "evidence/notion.jsonl"]

quality = []      # data-quality notes (strings)
mismatches = []   # verification failures (dicts)
checks = []       # verification checks run (dicts)


def check(name, ok, detail=""):
    checks.append({"check": name, "ok": bool(ok), "detail": detail})
    if not ok:
        mismatches.append({"check": name, "detail": detail})


def rp(p):
    return os.path.join(OUT, p)


def split_name(full):
    m = re.match(r"^(.*?)\s*\((.*)\)\s*$", full)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return full.strip(), None


def short(full):
    return split_name(full)[0].split()[0]


# ---------------------------------------------------------------- evidence
evidence = []
per_file_counts = {}
for f in EVIDENCE_FILES:
    rows = []
    with open(rp(f), encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    per_file_counts[f] = len(rows)
    for i, r in enumerate(rows, 1):
        missing = [k for k in ("source", "author", "timestamp", "text", "link") if k not in r]
        if missing:
            quality.append(f"{f} row {i}: missing fields {missing}")
        link = r.get("link") or ""
        if f.endswith("/call.jsonl") or f.endswith("/call-context.jsonl"):
            prefix = "call" if f.endswith("/call.jsonl") else "call-context"
            m = re.match(r"calls/([^/.#]+)\.md#(Q\d+)", link)
            eid = f"{prefix}:{m.group(1)}:{m.group(2)}" if m else f"{prefix}:{i}"
        elif f.endswith("linear.jsonl"):
            eid = link if re.match(r"^[A-Z]+-\d+$", link) else f"linear:{i}"
        else:
            eid = f"notion-{i:03d}"
        text = r.get("text") or ""
        author = r.get("author") or ""
        if author == "mentor notes":
            item_type = "mentor_note"
        elif r.get("source") == "notion" and not (text.startswith('"') and text.endswith('"')):
            item_type = "paraphrase"
        elif f.endswith("call-context.jsonl"):
            item_type = "call_context_answer"
        elif r.get("source") == "call":
            item_type = "call_answer"
        else:
            item_type = "founder_quote"
        evidence.append(dict(id=eid, source=r.get("source"), author=author,
                             timestamp=r.get("timestamp"), text=text, link=link,
                             file=f, item_type=item_type))

ev_by_id = {e["id"]: e for e in evidence}
check("evidence ids unique", len(ev_by_id) == len(evidence),
      f"{len(evidence)} rows, {len(ev_by_id)} unique ids")

seen, dups = {}, []
for e in evidence:
    k = (e["author"], e["text"].strip().strip('"'))
    if k in seen:
        dups.append((seen[k], e["id"]))
    seen[k] = e["id"]
no_ts = [e["id"] for e in evidence if not e["timestamp"]]
paraphrases = [e["id"] for e in evidence if e["item_type"] == "paraphrase"]
mentor = [e["id"] for e in evidence if e["item_type"] == "mentor_note"]

# ---------------------------------------------------------------- clusters.json
cj = json.load(open(rp("clusters.json"), encoding="utf-8"))
clusters = cj["clusters"]


def norm_status(s):
    s = (s or "").lower()
    if s.startswith("grew"):
        return "growing"
    if s.startswith("new"):
        return "new"
    return "unchanged"   # 'unchanged' and 'carried (no evidence in this run)'


# ---------------------------------------------------------------- pain library
lib = {}
for fn in sorted(os.listdir(LIB)):
    if not fn.endswith(".md") or fn.startswith("_"):
        continue
    txt = open(os.path.join(LIB, fn), encoding="utf-8").read()

    def g(pat):
        mm = re.search(pat, txt, re.M)
        return mm.group(1).strip() if mm else None

    cid = g(r"^- id:\s*(\S+)")
    hist_this = [l for l in txt.splitlines() if re.match(r"^- \d{4}-\d{2}-\d{2} ", l) and RUN_ID in l]
    if hist_this:
        h = hist_this[-1].lower()
        lib_status = "new" if "created" in h else ("growing" if "grew" in h else "unchanged")
    else:
        lib_status = "unchanged"
    refs = []
    sec = re.search(r"## Founders \(count each once\)\n(.*?)\n## ", txt, re.S)
    for line in (sec.group(1).splitlines() if sec else []):
        mm = re.match(r"^- (.+?):\s+(.*)$", line.strip())
        if not mm:
            continue
        founder = re.sub(r"\s*\(live founder.*\)$", "", mm.group(1).strip())
        for ref in [x.strip() for x in mm.group(2).split(",")]:
            src, _, loc = ref.partition(":")
            refs.append((founder, src, loc))
    lib[cid] = dict(
        file=fn, kind=g(r"^- kind:\s*(\S+)"),
        distinct_founders=int(g(r"^- distinct_founders:\s*(\d+)")),
        first_seen=g(r"^- first_seen:\s*(\d{4}-\d{2}-\d{2})"),
        first_seen_run=g(r"^- first_seen:.*\(run (\S+)\)"),
        last_seen=g(r"^- last_seen:\s*(\d{4}-\d{2}-\d{2})"),
        last_seen_run=g(r"^- last_seen:.*\(run (\S+)\)"),
        primitives=[p.strip() for p in (g(r"^- primitives:\s*(.*)$") or "").split(",") if p.strip()],
        status=lib_status, refs=refs)

index_txt = open(os.path.join(LIB, "_index.md"), encoding="utf-8").read()


def md_table_after(text, heading_regex):
    m = re.search(heading_regex, text, re.M)
    if not m:
        return []
    rows, started = [], False
    for line in text[m.end():].splitlines():
        if line.startswith("|"):
            started = True
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            rows.append(cells)
        elif started:
            break
    return rows[1:]  # drop header


founder_prims = {r[0]: [p.strip() for p in r[1].split(",")]
                 for r in md_table_after(index_txt, r"^Primitive attribution for the earlier founders")}
idx_tally = {r[0]: int(r[1]) for r in md_table_after(index_txt, r"^Founder-level primitive tally")}
idx_clusters = {re.sub(r"\s*\(requirement\)", "", r[0]): int(r[1])
                for r in md_table_after(index_txt, r"^# Pain library index")}
m = re.search(r"Distinct founders across the library:\s*(\d+)", index_txt)
lib_distinct_founders = int(m.group(1)) if m else None
m = re.search(r"The \d+ from " + re.escape(PREV_RUN_ID) + r" are (.*?)\.\s", index_txt)
prev_founders = {x.strip().split()[0] for x in re.split(r",|\band\b", m.group(1)) if x.strip()} if m else set()
check("previous-run founder list parsed from _index.md", len(prev_founders) == 10, str(sorted(prev_founders)))

# ---------------------------------------------------------------- founders
all_founders = []
for c in clusters:
    for f in c["founders"]:
        if f not in all_founders:
            all_founders.append(f)
lib_full = {}
for L in lib.values():
    for founder, src, loc in L["refs"]:
        lib_full.setdefault(short(founder), founder)
founder_sources = {f: set() for f in all_founders}
for f in all_founders:
    for L in lib.values():
        for founder, src, loc in L["refs"]:
            if short(founder) == short(f):
                founder_sources[f].add("call" if src.startswith("call") else src)
    for e in evidence:
        if e["author"] == f and e["item_type"] != "mentor_note":
            founder_sources[f].add(e["source"])
founders_rows = []
for f in all_founders:
    name, company = split_name(f)
    brief = f"briefs/{name.split()[0].lower()}.md"
    has_brief = os.path.isfile(rp(brief)) and os.path.getsize(rp(brief)) > 0
    founders_rows.append(dict(name=name, company=company, full=f, short=short(f),
                              sources=",".join(sorted(founder_sources[f])),
                              has_brief=int(has_brief), brief_path=brief if has_brief else None,
                              in_this_run=int(any(e["author"] == f for e in evidence))))
new_f = [r["name"] for r in founders_rows if r["short"] not in prev_founders]

# ---------------------------------------------------------------- cluster <-> evidence
cluster_evidence = set()
quote_rows = []
for c in clusters:
    for q in c.get("quotes", []):
        hits = [e for e in evidence if e["file"] == q["evidence_file"] and e["link"] == q["link"]
                and q["quote"] in e["text"]]
        check(f"quote verbatim in evidence: {c['id']} / {q['quote'][:40]}", len(hits) == 1,
              f"{len(hits)} matching evidence rows")
        eid = hits[0]["id"] if hits else None
        if eid:
            cluster_evidence.add((c["id"], eid))
        quote_rows.append(dict(cluster_id=c["id"], evidence_id=eid, author=q["author"], source=q["source"],
                               link=q["link"], quote=q["quote"], verbatim=int(bool(hits)), role="quote"))
    for q in c.get("context", []):
        hits = [e for e in evidence if e["link"] == q["link"] and q["quote"] in e["text"]]
        check(f"context quote verbatim in evidence: {c['id']} / {q['quote'][:40]}", len(hits) == 1,
              f"{len(hits)} matching evidence rows")
        quote_rows.append(dict(cluster_id=c["id"], evidence_id=hits[0]["id"] if hits else None,
                               author=q["author"], source=q["source"], link=q["link"],
                               quote=q["quote"], verbatim=int(bool(hits)), role="context"))

lib_ref_rows, lib_links = [], set()
for cid, L in lib.items():
    for founder, src, loc in L["refs"]:
        eid = None
        if src in ("linear", "notion") and loc in ev_by_id:
            eid = loc
        elif src in ("call", "call-context"):
            m2 = re.match(r"calls/([^/.#]+)\.md#(Q\d+)", loc)
            if m2 and f"{src}:{m2.group(1)}:{m2.group(2)}" in ev_by_id:
                eid = f"{src}:{m2.group(1)}:{m2.group(2)}"
        lib_ref_rows.append(dict(cluster_id=cid, founder=founder, source=src, ref=loc,
                                 evidence_id=eid, in_this_run=int(eid is not None)))
        if eid:
            lib_links.add((cid, eid))
only_lib, only_cj = lib_links - cluster_evidence, cluster_evidence - lib_links
check("pain-library evidence refs == clusters.json quote evidence (this run's items)",
      not only_lib and not only_cj, f"library-only: {sorted(only_lib)}; clusters.json-only: {sorted(only_cj)}")
cluster_evidence |= lib_links

clustered_ids = {e for _, e in cluster_evidence}
context_ids = {q["evidence_id"] for q in quote_rows if q["role"] == "context" and q["evidence_id"]}
evidence_status = {}
for e in evidence:
    if e["id"] in clustered_ids:
        evidence_status[e["id"]] = ("clustered", "")
    elif e["id"] in context_ids:
        evidence_status[e["id"]] = ("context", "context for a cluster, not counted")
    else:
        note = ""
        for u in cj.get("unclustered", []):
            if u["link"] == e["link"] and u.get("author") in (None, e["author"]):
                if u.get("author") is None or e["item_type"] in ("paraphrase", "mentor_note"):
                    note = u["reason"]
        if e["item_type"] == "call_context_answer" and not note:
            note = "call context answer (use case / DoD / closing); not a blocker"
        evidence_status[e["id"]] = ("unclustered", note)

# ---------------------------------------------------------------- per-cluster consistency
for c in clusters:
    L = lib.get(c["id"])
    check(f"cluster in pain library: {c['id']}", L is not None, "")
    if not L:
        continue
    check(f"founder count clusters.json vs library: {c['id']}",
          c["distinct_founders"] == L["distinct_founders"] == len(c["founders"]),
          f"clusters.json {c['distinct_founders']} / founders[] {len(c['founders'])} / library {L['distinct_founders']}")
    check(f"founder count vs _index.md: {c['id']}", idx_clusters.get(c["id"]) == c["distinct_founders"],
          f"_index {idx_clusters.get(c['id'])} vs {c['distinct_founders']}")
    check(f"status clusters.json vs library history: {c['id']}", norm_status(c["status"]) == L["status"],
          f"clusters.json '{c['status']}' -> {norm_status(c['status'])}; library -> {L['status']}")
    check(f"primitives clusters.json vs library: {c['id']}", set(c["primitives"]) == set(L["primitives"]),
          f"{c['primitives']} vs {L['primitives']}")
    lf = {short(f) for f, _, _ in L["refs"]}
    check(f"founder names clusters.json vs library: {c['id']}", lf == {short(f) for f in c["founders"]},
          f"{sorted(lf)} vs {sorted(short(f) for f in c['founders'])}")

# ---------------------------------------------------------------- primitive tally
blockers = [c for c in clusters if c["kind"] == "blocker"]
blocker_founders = {short(f) for c in blockers for f in c["founders"]}
prim_founders, prim_clusters, prim_cluster_founders = {}, {}, {}
for fs, prims in founder_prims.items():
    if fs in blocker_founders:
        for p in prims:
            prim_founders.setdefault(p, []).append(fs)
for c in blockers:
    for p in c["primitives"]:
        prim_clusters.setdefault(p, []).append(c["id"])
        prim_cluster_founders.setdefault(p, set()).update(short(f) for f in c["founders"])
check("founder attribution covers every blocker founder", blocker_founders <= set(founder_prims),
      f"missing: {sorted(blocker_founders - set(founder_prims))}")
for p, n in idx_tally.items():
    check(f"primitive tally vs _index.md: {p}", len(prim_founders.get(p, [])) == n,
          f"computed {len(prim_founders.get(p, []))} vs _index {n}")
for fs, prims in founder_prims.items():
    cps = {p for c in blockers if fs in {short(f) for f in c["founders"]} for p in c["primitives"]}
    check(f"attribution consistent with founder's clusters: {fs}", set(prims) <= cps,
          f"attributed {prims}; cluster primitives {sorted(cps)}")

# ---------------------------------------------------------------- room-report.md
report = open(rp("room-report.md"), encoding="utf-8").read()
m = re.search(r"\*\*(\d+) distinct founders\*\*", report)
rep_founders = int(m.group(1)) if m else None
check("report distinct founders == clusters.json == library", rep_founders == len(all_founders) == lib_distinct_founders,
      f"report {rep_founders}, clusters.json {len(all_founders)}, library {lib_distinct_founders}")
chg = re.search(r"\*\*Change since last run:\*\*(.*)", report).group(1)
rep_grew = int(re.search(r"(\d+) clusters? grew", chg).group(1))
rep_new = int(re.search(r"(\d+) clusters are new", chg).group(1))
rep_unch = int(re.search(r"(\d+) clusters are unchanged", chg).group(1))
status_counts = {"new": 0, "growing": 0, "unchanged": 0}
for c in clusters:
    status_counts[norm_status(c["status"])] += 1
check("report change counts == computed",
      (rep_new, rep_grew, rep_unch) == (status_counts["new"], status_counts["growing"], status_counts["unchanged"]),
      f"report new/grew/unchanged {rep_new}/{rep_grew}/{rep_unch} vs computed {status_counts}")
check("report new founders == computed", "karan is the one new founder" in report and new_f == ["karan"], str(new_f))

ranked_rows = []
sec = report.split("## Clusters ranked by distinct founders")[1].split("\n### ")[0]
for line in sec.splitlines():
    mm = re.match(r"^\|\s*(\d+|—)\s*\|\s*([a-z-]+)[^|]*\|\s*(\d+)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|", line)
    if mm:
        ranked_rows.append(dict(rank=mm.group(1), id=mm.group(2), founders=int(mm.group(3)),
                                status=mm.group(4).strip(), sources=[s.strip() for s in mm.group(5).split(",")],
                                primitives=[s.strip() for s in mm.group(6).split(",")]))
check("report ranked table has every cluster", {r["id"] for r in ranked_rows} == {c["id"] for c in clusters},
      f"{len(ranked_rows)} rows")
for r in ranked_rows:
    c = next((x for x in clusters if x["id"] == r["id"]), None)
    if not c:
        continue
    rs = r["status"].replace("*", "").lower()
    rs_n = "growing" if rs.startswith("grew") else ("new" if rs.startswith("new") else "unchanged")
    ok = (r["founders"] == c["distinct_founders"] and rs_n == norm_status(c["status"])
          and set(r["sources"]) == set(c["sources"]) and set(r["primitives"]) == set(c["primitives"])
          and (r["rank"] == "—" or int(r["rank"]) == c["rank"]))
    check(f"report ranked row == clusters.json: {r['id']}", ok,
          f"report {r} vs clusters.json rank {c['rank']} founders {c['distinct_founders']} status {c['status']}")
# cluster section headers: "(N founders: names)"
for mm in re.finditer(r"^### (?:\d+\.|Requirement:) ([a-z-]+)[^\n]*?\((\d+) founders?: ([^)]*)\)", report, re.M):
    c = next((x for x in clusters if x["id"] == mm.group(1)), None)
    if c:
        names = {s.strip().split()[0] for s in mm.group(3).split(",")}
        check(f"report cluster heading founders == clusters.json: {c['id']}",
              int(mm.group(2)) == c["distinct_founders"] and names == {short(f) for f in c["founders"]},
              f"report {mm.group(2)} ({mm.group(3)}) vs {c['founders']}")

tally_sec = report.split("## Blocker tally by CMA primitive")[1]
rep_tally = {}
for line in tally_sec.splitlines():
    mm = re.match(r"^\|\s*([A-Za-z][A-Za-z ]+?)\s*\|\s*(\d+)\s*\|([^|]*)\|", line)
    if mm:
        rep_tally[mm.group(1)] = (int(mm.group(2)), [s.strip() for s in mm.group(3).split(",")])
check("report tally primitives == computed", set(rep_tally) == set(prim_founders),
      f"report {sorted(rep_tally)} vs computed {sorted(prim_founders)}")
for p, (n, names) in rep_tally.items():
    comp = prim_founders.get(p, [])
    check(f"report tally row == computed: {p}", n == len(comp) and set(names) == set(comp),
          f"report {n} {names} vs computed {len(comp)} {comp}")
check("report ends with the tally table", report.rstrip().splitlines()[-1].startswith("|")
      and report.rfind("\n## ") == report.find("\n## Blocker tally by CMA primitive"), "")

top_sec = report.split("## Top 3 fixes")[1].split("\n---")[0]
rep_top = re.findall(r"^### (\d)\. .*?: (\d+) founders \(([^)]*)\)", top_sec, re.M)
check("report has 3 top fixes", len(rep_top) == 3 == len(cj["top3_fixes"]), f"{len(rep_top)}")
for rank, n, names in rep_top:
    t = next((x for x in cj["top3_fixes"] if x["rank"] == int(rank)), None)
    ok = t is not None and int(n) == len(t["founders_served"]) and \
        {s.strip() for s in names.split(",")} == {short(f) for f in t["founders_served"]}
    check(f"report top fix #{rank} founders == clusters.json", ok, f"report {n} ({names}) vs {t and t['founders_served']}")
for t in cj["top3_fixes"]:
    union = []
    for cid in t["fix_for"]:
        union += [f for f in next(x for x in clusters if x["id"] == cid)["founders"] if f not in union]
    check(f"top fix #{t['rank']} founders_served == union of its clusters' founders",
          set(union) == set(t["founders_served"]), f"{union} vs {t['founders_served']}")
for block in re.split(r"^### ", top_sec, flags=re.M)[1:]:
    rank = int(block[0])
    t = next(x for x in cj["top3_fixes"] if x["rank"] == rank)
    allowed = {q["quote"] for cid in t["fix_for"] for q in next(x for x in clusters if x["id"] == cid)["quotes"]}
    for q in re.findall(r'^- "([^"]+)"', block, re.M):
        check(f"report top fix #{rank} quote is a clusters.json quote", q in allowed, q[:60])

rep_quotes = re.findall(r'"([^"]+)"', report)
nonverb = [q for q in rep_quotes if not any(q in e["text"] for e in evidence)]
check("every double-quoted string in room-report.md is verbatim evidence", not nonverb,
      f"{len(rep_quotes)} quoted strings; not found: {nonverb}")
karan_clusters = [c["id"] for c in clusters if "karan" in c["founders"]]
m = re.search(r"karan counts once in each of (\w+) clusters", report)
words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
check("report 'karan counts once in each of N clusters'", bool(m) and words.get(m.group(1)) == len(karan_clusters),
      f"{m and m.group(1)} vs {karan_clusters}")
m = re.search(r"Blocker tally by CMA primitive.*?match the last run's totals \(deployment (\d+), session (\d+), multiagent (\d+)\)",
              report, re.S)
# last-run totals = this run minus karan's attributions
if m:
    lr = {p: len([f for f in prim_founders.get(p, []) if f != "karan"]) for p in ("deployment", "session", "multiagent")}
    check("report 'last run totals' == computed minus karan",
          (int(m.group(1)), int(m.group(2)), int(m.group(3))) == (lr["deployment"], lr["session"], lr["multiagent"]),
          f"report {m.groups()} vs {lr}")

# ---------------------------------------------------------------- per-agent check
manifest = json.load(open(rp("run-manifest.json"), encoding="utf-8"))
threads = json.load(open(rp("work/threads.json"), encoding="utf-8"))
thread_ids_in_notes = {}
for s in manifest["steps"]:
    for tid in re.findall(r"sthr_[A-Za-z0-9]+", s.get("notes", "")):
        thread_ids_in_notes[tid] = s["step"]

DA_EXPECTED = ["data/room.db", "data/metrics.json", "dashboard.html"]  # from the coordinator's dispatch
nb = sum(1 for c in clusters if c["kind"] == "blocker")
nr = sum(1 for c in clusters if c["kind"] == "requirement")


def claims_for(step):
    """Check the numeric claims in a step's manifest notes against the files on disk."""
    n, out = step.get("notes", ""), []
    if step["step"] == 1:
        m1 = re.search(r"(\d+)/(\d+) questions", n)
        t = open(rp("calls/karan.md"), encoding="utf-8").read()
        qn, an = len(re.findall(r"^Q:", t, re.M)), len(re.findall(r"^A:", t, re.M))
        out.append(dict(claim=m1.group(0) if m1 else "question count", observed=f"{qn} Q / {an} A in calls/karan.md",
                        ok=bool(m1) and int(m1.group(1)) == qn == an))
        b = open(rp("briefs/karan.md"), encoding="utf-8").read()
        fields = ["use_case", "current_workaround", "blockers", "definition_of_done", "cma_mapping"]
        present = [f for f in fields if f"**{f}:**" in b]
        out.append(dict(claim="needs brief has the 5 standard fields", observed=f"{len(present)}/5 present",
                        ok=len(present) == 5))
    elif step["step"] in (2, 3):
        m1 = re.search(r"(\d+) items", n)
        f = step["outputs"][0]
        rows = [json.loads(l) for l in open(rp(f), encoding="utf-8") if l.strip()]
        five = all(set(r) == {"source", "author", "timestamp", "text", "link"} for r in rows)
        out.append(dict(claim=m1.group(0) if m1 else "item count", observed=f"{len(rows)} rows in {f}",
                        ok=bool(m1) and int(m1.group(1)) == len(rows)))
        out.append(dict(claim="every row has exactly the 5 standard fields", observed="yes" if five else "no", ok=five))
    elif step["step"] == 4:
        m1 = re.search(r"(\d+) clusters \+ (\d+) requirement across (\d+) founders", n)
        out.append(dict(claim=m1.group(0) if m1 else "cluster counts",
                        observed=f"{nb} blockers + {nr} requirement, {len(all_founders)} founders in clusters.json",
                        ok=bool(m1) and tuple(map(int, m1.groups())) == (nb, nr, len(all_founders))))
        m2 = re.search(r"(\d+) new clusters", n)
        out.append(dict(claim=m2.group(0) if m2 else "new clusters", observed=f"{status_counts['new']} new in clusters.json",
                        ok=bool(m2) and int(m2.group(1)) == status_counts["new"]))
        m3 = re.search(r"run-opacity grew to (\d+)", n)
        ro = next(c for c in clusters if c["id"] == "run-opacity")
        out.append(dict(claim=m3.group(0) if m3 else "run-opacity growth",
                        observed=f"run-opacity {ro['distinct_founders']} founders, status '{ro['status']}'",
                        ok=bool(m3) and int(m3.group(1)) == ro["distinct_founders"] and ro["status"] == "grew"))
        vq = [q for q in quote_rows if q["role"] == "quote"]
        out.append(dict(claim="cluster quotes are verbatim evidence",
                        observed=f"{sum(q['verbatim'] for q in vq)}/{len(vq)} verbatim", ok=all(q["verbatim"] for q in vq)))
        out.append(dict(claim="report quotes are verbatim evidence",
                        observed=f"{len(rep_quotes) - len(nonverb)}/{len(rep_quotes)} verbatim", ok=not nonverb))
        out.append(dict(claim="report has a Top 3 fixes section with quotes",
                        observed=f"{len(rep_top)} fixes in report, {len(cj['top3_fixes'])} in clusters.json",
                        ok=len(rep_top) == 3 == len(cj["top3_fixes"])))
    return out


def safe_claims(step):
    try:
        return claims_for(step)
    except (OSError, ValueError, IndexError, KeyError) as exc:
        return [dict(claim="claims in manifest notes are checkable", observed=f"error: {type(exc).__name__}: {exc}", ok=False)]


agent_steps = []
for s in manifest["steps"]:
    agent = ", ".join(s["delegated_to"])
    is_self = "data-analyst" in agent
    expected = s["outputs"] if s["outputs"] else (DA_EXPECTED if is_self else [])
    files = []
    for f in expected:
        ex = os.path.isfile(rp(f))
        files.append(dict(path=f, exists=ex, bytes=os.path.getsize(rp(f)) if ex else 0))
    step_threads = [t for t, st in thread_ids_in_notes.items() if st == s["step"]]
    if is_self:
        verdict, claims = "self-check (not counted)", []
        note = ("The manifest lists no outputs for this step yet (status in_progress), so the expected outputs "
                "come from the coordinator's dispatch. Files present reflect the moment metrics.json was built. "
                "An agent can't certify its own step: the coordinator should re-run this check after step 5.")
    else:
        claims = safe_claims(s)
        files_ok = bool(files) and all(f["exists"] and f["bytes"] > 0 for f in files)
        verdict = "pass" if files_ok and all(c["ok"] for c in claims) else "fail"
        note = ""
    agent_steps.append(dict(step=s["step"], agent=agent, task=s["task"], manifest_status=s["status"],
                            expected_outputs=files, files_expected=len(files),
                            files_present=sum(1 for f in files if f["exists"] and f["bytes"] > 0),
                            claims=claims, claims_ok=sum(1 for c in claims if c["ok"]), verdict=verdict, note=note,
                            thread_ids=step_threads, thread_recorded=bool(step_threads), cost="not available"))

thread_rows = []
for founder, roles in threads.items():
    for role, tid in roles.items():
        if not str(tid).startswith("sthr_"):
            thread_rows.append(dict(founder=founder, role=role, thread_id=None, step=None,
                                    status="not an agent thread", detail=str(tid), cost="not available"))
            continue
        st = thread_ids_in_notes.get(tid)
        thread_rows.append(dict(founder=founder, role=role, thread_id=tid, step=st,
                                status="used (matches manifest step)" if st else "STRAY (no manifest step)",
                                detail="", cost="not available"))
recorded = {t["thread_id"] for t in thread_rows if t["thread_id"]}
for tid, st in thread_ids_in_notes.items():
    if tid not in recorded:
        thread_rows.append(dict(founder=manifest.get("founder"), role=f"step {st}", thread_id=tid, step=st,
                                status="in manifest but missing from threads.json", detail="", cost="not available"))
stray = [t for t in thread_rows if t["status"].startswith("STRAY")]
unrecorded_steps = [a["step"] for a in agent_steps if not a["thread_recorded"]]
checked = [a for a in agent_steps if a["verdict"] in ("pass", "fail")]
agent_summary = dict(steps_checked=len(checked),
                     passed=sum(1 for a in checked if a["verdict"] == "pass"),
                     failed=sum(1 for a in checked if a["verdict"] == "fail"),
                     self_check_steps=[a["step"] for a in agent_steps if a["verdict"].startswith("self")],
                     agent_threads_recorded=len([t for t in thread_rows if t["thread_id"]]),
                     stray_threads=len(stray),
                     steps_without_recorded_thread=unrecorded_steps)

cost_spec = {
    "status": "not_available",
    "reason": "No token or billing telemetry is available to the data analyst in this session. "
              "No cost numbers are shown or estimated.",
    "unit_of_analysis": "one agent thread (sthr_*) per specialist step; rolled up to step and run",
    "source": "session event stream: per-thread model-usage events (input/output/cache tokens) tagged with "
              "thread_id and agent name, priced at the model's per-token rates at run time",
    "fields_per_thread": {
        "thread_id": "sthr_* id",
        "agent": "agent name (e.g. room-miner-linear-scout)",
        "step": "run-manifest step number, or null if the thread matches no step (stray)",
        "input_tokens": "sum over the thread's model calls",
        "output_tokens": "sum over the thread's model calls",
        "cache_read_tokens": "sum over the thread's model calls",
        "cache_write_tokens": "sum over the thread's model calls",
        "model_calls": "count of model requests",
        "tool_calls": "count of tool invocations",
        "wall_clock_s": "first to last event in the thread",
        "cost_usd": "tokens x per-token price for the model used"
    },
    "derived_metrics": {
        "cost_per_step_usd": "sum of cost_usd over threads mapped to the step",
        "run_total_cost_usd": "sum of cost_usd over all threads in the run",
        "wasted_thread_cost_usd": "sum of cost_usd over threads flagged STRAY plus threads of steps with verdict fail",
        "cost_per_passing_step_usd": "run_total_cost_usd / number of steps with verdict pass",
        "cost_per_top3_fix_usd": "run_total_cost_usd / 3 (cost of producing Monday's list)"
    },
    "ready_when": "threads.json (or the event stream) records every thread the coordinator spawned, including "
                  "miner and data-analyst threads, and usage events carry thread_id"
}

# ---------------------------------------------------------------- metrics
top_clusters = [dict(rank=c["rank"], id=c["id"], name=c["name"], kind=c["kind"],
                     founders=c["distinct_founders"], founder_names=[split_name(f)[0] for f in c["founders"]],
                     status=norm_status(c["status"]), status_raw=c["status"],
                     sources=c["sources"], primitives=c["primitives"],
                     paused=[split_name(f)[0] for f in c.get("paused", [])],
                     quotes_this_run=len(c.get("quotes", [])),
                     evidence_items_this_run=len({e for cid, e in cluster_evidence if cid == c["id"]}),
                     first_seen=lib[c["id"]]["first_seen"], last_seen=lib[c["id"]]["last_seen"],
                     fix=c.get("fix"))
                for c in sorted(clusters, key=lambda x: x["rank"])]

top3 = []
for t in sorted(cj["top3_fixes"], key=lambda x: x["rank"]):
    qs = []
    for cid in t["fix_for"]:
        for q in next(x for x in clusters if x["id"] == cid)["quotes"]:
            if not any(q["quote"] == y["quote"] for y in qs):
                qs.append(dict(quote=q["quote"], author=split_name(q["author"])[0], source=q["source"],
                               link=q["link"], cluster=cid,
                               verbatim=any(r["verbatim"] for r in quote_rows if r["quote"] == q["quote"])))
    top3.append(dict(rank=t["rank"], fix_for=t["fix_for"], founders_served=len(t["founders_served"]),
                     founder_names=[split_name(f)[0] for f in t["founders_served"]], fix=t["fix"], quotes=qs))


def tally(items):
    d = {}
    for k in items:
        d[k] = d.get(k, 0) + 1
    return d


ev_per_source = tally(e["source"] for e in evidence)
founders_per_source = tally(s for r in founders_rows for s in r["sources"].split(","))
clusters_per_source = tally(s for c in blockers for s in c["sources"])
quotes_per_source = tally(q["source"] for q in quote_rows if q["role"] == "quote")
paused = sorted({split_name(f)[0] for c in clusters for f in c.get("paused", [])})
no_ev_clusters = [c["id"] for c in clusters if not any(cid == c["id"] for cid, _ in cluster_evidence)]
lib_only = [r["name"] for r in founders_rows if not r["in_this_run"]]

quality = [
    "No evidence file has an id field; ids were synthesised: call:<slug>:Q<n>, call-context:<slug>:Q<n>, "
    "FFD-<n> (Linear link), notion-00<n> (file order; matches the pain library's notion-00n refs).",
    f"Missing timestamps: {len(no_ts)} of {len(evidence)} evidence items (all call and Notion items). Only the "
    f"{ev_per_source.get('linear', 0)} Linear items are dated.",
    f"Exact duplicate evidence items (same author and text): {len(dups)}{(' ' + str(dups)) if dups else ''}.",
    f"Paraphrase attributed to a founder: {', '.join(paraphrases)} (a note-taker paraphrase stored under Omar Haddad; "
    "the fixed schema has no type field). It is not quoted anywhere.",
    f"Items not from a founder: {', '.join(mentor)} (author 'mentor notes'). Used as context only.",
    "The Linear and Notion exports are labelled seed/mock data, and they are the same items counted in the 2026-09-23 "
    "EVAL run. The Linear export has no status field, so open/closed state is unknown.",
    f"Founders counted from the pain library only (their call transcripts are not in this run's outputs): "
    f"{', '.join(lib_only)}. Clusters with no evidence in this run: {', '.join(no_ev_clusters)}.",
    "Notion links point to /mnt/session/uploads/..., which is outside the outputs folder.",
    "karan's Q3, Q5 and Q6 each support two clusters (Q3: multiagent-misrouting and context-rot-task-drift; "
    "Q5 and Q6: run-opacity and unverified-completion). This is multi-mapping, not duplication, and founder counts "
    "stay distinct per cluster.",
    "karan's Q5 answer begins 'All three:', but the recorded question lists no options. The question may have been "
    "leading, or the transcript may be incomplete (the miner flagged this too).",
    "Ben's 'company' is a descriptor (climate-investor newsletter), not a company name. karan has no company recorded.",
    f"threads.json records {agent_summary['agent_threads_recorded']} agent threads (discovery, notion-scout, "
    f"linear-scout). Steps {', '.join(map(str, unrecorded_steps))} (miner, data-analyst) have no recorded thread id, so the stray-thread "
    "check cannot see them.",
    "work/pending-triggers.json still says 'deferred until CALL COMPLETE', although the manifest shows those steps as "
    "done or in progress (stale status field).",
    "The data-analyst prompt names /mnt/memory/pain-library/; the real store is /mnt/memory/room-miner-pain-library/. "
    "The miner had already updated it for this run, so new/growing status comes from its History lines.",
    "No cost or token telemetry is available in this session, so every cost cell reads 'not available' by design.",
] + quality

metrics = {
    "run": RUN_ID, "previous_run": PREV_RUN_ID, "mode": manifest.get("mode"), "founder": manifest.get("founder"),
    "generated_by": "data/build.py",
    "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "headline": {
        "distinct_founders": len(all_founders),
        "new_founders_this_run": len(new_f), "new_founder_names": new_f,
        "founders_evidenced_this_run": sum(r["in_this_run"] for r in founders_rows),
        "founders_paused_or_stopped": len(paused), "founders_paused_or_stopped_names": paused,
        "clusters_total": len(clusters), "blocker_clusters": nb, "requirement_clusters": nr,
        "clusters_new": status_counts["new"], "clusters_growing": status_counts["growing"],
        "clusters_unchanged": status_counts["unchanged"],
        "evidence_items_this_run": len(evidence),
        "cluster_quotes": sum(1 for q in quote_rows if q["role"] == "quote"),
        "cluster_quotes_verbatim": sum(q["verbatim"] for q in quote_rows if q["role"] == "quote"),
        "report_quotes": len(rep_quotes), "report_quotes_verbatim": len(rep_quotes) - len(nonverb),
        "agent_steps_checked": agent_summary["steps_checked"], "agent_steps_passed": agent_summary["passed"],
        "stray_threads": agent_summary["stray_threads"],
        "run_cost": "not available",
        "mismatches_vs_report": None,
    },
    "founder_definition_of_done": next(({"quote": e["text"], "author": e["author"], "link": e["link"],
                                         "evidence_id": e["id"]} for e in evidence
                                        if e["link"].endswith("#Q6") and e["file"].endswith("call-context.jsonl")), None),
    "top3_fixes": top3,
    "top_clusters_by_founders": top_clusters,
    "pains_by_primitive": {
        "method": "Founder-level: a primitive counts a founder only where that founder's own evidence implicates it "
                  "(attribution from pain-library _index.md; blocker clusters only). Same method as the room-report.md tally.",
        "rows": sorted([dict(primitive=p, founders=len(v), founder_names=v,
                             blocker_clusters=len(prim_clusters.get(p, [])), cluster_ids=prim_clusters.get(p, []),
                             founders_if_counted_per_cluster=len(prim_cluster_founders.get(p, set())))
                        for p, v in prim_founders.items()],
                       key=lambda r: (-r["founders"], -r["blocker_clusters"], r["primitive"])),
    },
    "pains_by_source": {
        "blocker_clusters_citing_source": clusters_per_source,
        "founders_by_source": founders_per_source,
        "cluster_quotes_by_source": quotes_per_source,
    },
    "evidence_items_per_source": ev_per_source,
    "evidence_items_per_file": per_file_counts,
    "founders_per_cluster": {c["id"]: c["distinct_founders"] for c in sorted(clusters, key=lambda x: x["rank"])},
    "cluster_status_vs_last_run": {
        "method": "clusters.json status, cross-checked with the pain-library History line for this run "
                  "(created -> new, GREW -> growing, anything else -> unchanged; 'carried' counts as unchanged)",
        "counts": status_counts,
        "new": [c["id"] for c in clusters if norm_status(c["status"]) == "new"],
        "growing": [dict(id=c["id"], founders=c["distinct_founders"],
                         added=[split_name(f)[0] for f in c["founders"] if short(f) not in prev_founders])
                    for c in clusters if norm_status(c["status"]) == "growing"],
        "unchanged": [c["id"] for c in clusters if norm_status(c["status"]) == "unchanged"],
        "unchanged_carried_without_evidence": [c["id"] for c in clusters if c["status"].startswith("carried")],
    },
    "coverage": {
        "founders_total": len(founders_rows),
        "founders_with_brief": sum(r["has_brief"] for r in founders_rows),
        "founders_with_brief_names": [r["name"] for r in founders_rows if r["has_brief"]],
        "founders_called_this_run": len([f for f in threads if threads[f].get("discovery")]),
        "founders_called_this_run_with_brief": sum(1 for f in threads if os.path.isfile(rp(f"briefs/{f}.md"))),
        "founders_counted_from_library_only": lib_only,
        "sources_expected": ["call", "linear", "notion"],
        "sources_with_zero_items": [s for s in ["call", "linear", "notion"] if ev_per_source.get(s, 0) == 0],
        "evidence_files_with_zero_rows": [f for f, n in per_file_counts.items() if n == 0],
        "clusters_with_no_evidence_this_run": no_ev_clusters,
        "evidence_items_clustered": sum(1 for v in evidence_status.values() if v[0] == "clustered"),
        "evidence_items_context_only": sum(1 for v in evidence_status.values() if v[0] == "context"),
        "evidence_items_unclustered": [dict(id=k, note=v[1]) for k, v in evidence_status.items() if v[0] == "unclustered"],
    },
    "agent_check": {"summary": agent_summary, "steps": agent_steps, "threads": thread_rows},
    "cost": {"display": "not available",
             "per_step": {str(a["step"]): "not available" for a in agent_steps},
             "per_thread": {t["thread_id"]: "not available" for t in thread_rows if t["thread_id"]},
             "spec": cost_spec},
    "data_quality": quality,
    "verification": {},
}

# ---------------------------------------------------------------- sqlite
os.makedirs(DATA, exist_ok=True)
dbp = os.path.join(DATA, "room.db")
if os.path.exists(dbp):
    os.remove(dbp)
db = sqlite3.connect(dbp)
db.executescript("""
CREATE TABLE evidence(id TEXT PRIMARY KEY, source TEXT, author TEXT, timestamp TEXT, text TEXT, link TEXT,
                      file TEXT, item_type TEXT, cluster_status TEXT, note TEXT);
CREATE TABLE founders(name TEXT PRIMARY KEY, company TEXT, sources TEXT, has_brief INTEGER,
                      brief_path TEXT, in_this_run INTEGER, primitives TEXT, label TEXT);
CREATE TABLE clusters(id TEXT PRIMARY KEY, name TEXT, primitive TEXT, first_seen TEXT, last_seen TEXT,
                      founder_count INTEGER, kind TEXT, rank INTEGER, status TEXT, sources TEXT, fix TEXT);
CREATE TABLE cluster_evidence(cluster_id TEXT, evidence_id TEXT, PRIMARY KEY(cluster_id, evidence_id));
CREATE TABLE cluster_founders(cluster_id TEXT, founder TEXT, evidenced_this_run INTEGER, paused INTEGER);
CREATE TABLE cluster_primitives(cluster_id TEXT, primitive TEXT);
CREATE TABLE founder_primitives(founder TEXT, primitive TEXT);
CREATE TABLE library_refs(cluster_id TEXT, founder TEXT, source TEXT, ref TEXT, evidence_id TEXT, in_this_run INTEGER);
CREATE TABLE quotes(cluster_id TEXT, evidence_id TEXT, author TEXT, source TEXT, link TEXT, quote TEXT,
                    verbatim INTEGER, role TEXT);
CREATE TABLE top3_fixes(rank INTEGER, fix TEXT, fix_for TEXT, founders_served INTEGER, founder_names TEXT);
CREATE TABLE agent_checks(step INTEGER, agent TEXT, expected_output TEXT, exists_on_disk INTEGER, bytes INTEGER,
                          verdict TEXT, thread_id TEXT, cost TEXT);
CREATE TABLE agent_claims(step INTEGER, claim TEXT, observed TEXT, ok INTEGER);
CREATE TABLE threads(founder TEXT, role TEXT, thread_id TEXT, step INTEGER, status TEXT, cost TEXT);
""")
for e in evidence:
    st, note = evidence_status[e["id"]]
    db.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?)",
               (e["id"], e["source"], e["author"], e["timestamp"], e["text"], e["link"], e["file"], e["item_type"], st, note))
for r in founders_rows:
    db.execute("INSERT INTO founders VALUES(?,?,?,?,?,?,?,?)",
               (r["name"], r["company"], r["sources"], r["has_brief"], r["brief_path"], r["in_this_run"],
                ", ".join(founder_prims.get(r["short"], [])), r["full"]))
for c in clusters:
    L = lib[c["id"]]
    db.execute("INSERT INTO clusters VALUES(?,?,?,?,?,?,?,?,?,?,?)",
               (c["id"], c["name"], ", ".join(c["primitives"]), L["first_seen"], L["last_seen"], c["distinct_founders"],
                c["kind"], c["rank"], norm_status(c["status"]), ", ".join(c["sources"]), c.get("fix")))
    for f in c["founders"]:
        db.execute("INSERT INTO cluster_founders VALUES(?,?,?,?)",
                   (c["id"], split_name(f)[0], int(f in c.get("founders_evidenced_this_run", [])), int(f in c.get("paused", []))))
    for p in c["primitives"]:
        db.execute("INSERT INTO cluster_primitives VALUES(?,?)", (c["id"], p))
for cid, eid in sorted(cluster_evidence):
    db.execute("INSERT INTO cluster_evidence VALUES(?,?)", (cid, eid))
for fs, prims in founder_prims.items():
    for p in prims:
        db.execute("INSERT INTO founder_primitives VALUES(?,?)", (split_name(lib_full.get(fs, fs))[0], p))
for r in lib_ref_rows:
    db.execute("INSERT INTO library_refs VALUES(?,?,?,?,?,?)",
               (r["cluster_id"], r["founder"], r["source"], r["ref"], r["evidence_id"], r["in_this_run"]))
for q in quote_rows:
    db.execute("INSERT INTO quotes VALUES(?,?,?,?,?,?,?,?)",
               (q["cluster_id"], q["evidence_id"], q["author"], q["source"], q["link"], q["quote"], q["verbatim"], q["role"]))
for t in cj["top3_fixes"]:
    db.execute("INSERT INTO top3_fixes VALUES(?,?,?,?,?)",
               (t["rank"], t["fix"], ",".join(t["fix_for"]), len(t["founders_served"]), ", ".join(t["founders_served"])))
for a in agent_steps:
    for f in a["expected_outputs"]:
        db.execute("INSERT INTO agent_checks VALUES(?,?,?,?,?,?,?,?)",
                   (a["step"], a["agent"], f["path"], int(f["exists"]), f["bytes"], a["verdict"],
                    ",".join(a["thread_ids"]) or None, "not available"))
    for c in a["claims"]:
        db.execute("INSERT INTO agent_claims VALUES(?,?,?,?)", (a["step"], c["claim"], c["observed"], int(c["ok"])))
for t in thread_rows:
    db.execute("INSERT INTO threads VALUES(?,?,?,?,?,?)",
               (t["founder"], t["role"], t["thread_id"], t["step"], t["status"], t["cost"]))
db.commit()

# SQL cross-checks: the DB must reproduce the headline numbers
q1 = db.execute("SELECT COUNT(*) FROM founders").fetchone()[0]
check("room.db founders == distinct founders", q1 == len(all_founders), f"{q1}")
q2 = dict(db.execute("SELECT status, COUNT(*) FROM clusters GROUP BY status").fetchall())
check("room.db cluster status counts == metrics", q2 == {k: v for k, v in status_counts.items() if v}, str(q2))
q3 = dict(db.execute("SELECT primitive, COUNT(DISTINCT founder) FROM founder_primitives fp "
                     "WHERE founder IN (SELECT founder FROM cluster_founders cf JOIN clusters c ON c.id=cf.cluster_id "
                     "WHERE c.kind='blocker') GROUP BY primitive").fetchall())
check("room.db primitive tally == metrics", q3 == {p: len(v) for p, v in prim_founders.items()}, str(q3))
q4 = dict(db.execute("SELECT cluster_id, COUNT(*) FROM cluster_founders GROUP BY cluster_id").fetchall())
check("room.db founders per cluster == clusters.founder_count",
      all(q4[c["id"]] == c["distinct_founders"] for c in clusters), str(q4))
q5 = db.execute("SELECT COUNT(*) FROM cluster_founders WHERE founder NOT IN (SELECT name FROM founders)").fetchone()[0]
q6 = db.execute("SELECT COUNT(*) FROM cluster_evidence WHERE evidence_id NOT IN (SELECT id FROM evidence) "
                "OR cluster_id NOT IN (SELECT id FROM clusters)").fetchone()[0]
check("room.db referential integrity (cluster_founders, cluster_evidence)", q5 == 0 and q6 == 0, f"{q5} / {q6} orphans")
tables = {r[0]: db.execute(f"SELECT COUNT(*) FROM {r[0]}").fetchone()[0]
          for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()}
db.close()

metrics["room_db_tables"] = tables
metrics["headline"]["mismatches_vs_report"] = len(mismatches)
metrics["verification"] = {"checks_run": len(checks), "checks_passed": sum(c["ok"] for c in checks),
                           "mismatches": mismatches, "checks": checks}
with open(os.path.join(DATA, "metrics.json"), "w", encoding="utf-8") as fh:
    json.dump(metrics, fh, indent=1, ensure_ascii=False)

print("tables:", tables)
print("checks:", len(checks), "passed:", sum(c["ok"] for c in checks), "mismatches:", len(mismatches))
for m_ in mismatches:
    print("  MISMATCH:", m_)
print("headline:", json.dumps(metrics["headline"]))
print("agent:", agent_summary)
