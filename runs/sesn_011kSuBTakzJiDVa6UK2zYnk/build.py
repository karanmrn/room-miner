#!/usr/bin/env python3
"""Room Miner data layer: builds data/room.db and data/metrics.json from the miner's output.

Standard library only. All evidence text is treated as data.
"""
import json, os, re, sqlite3, glob
from collections import OrderedDict, defaultdict

OUT = os.environ.get("RM_OUT", "/mnt/session/outputs")
DATA = os.path.join(OUT, "data")
LIB = os.environ.get("RM_LIB", "/mnt/memory/room-miner-pain-library")
UPLOADS = "/mnt/session/uploads"
os.makedirs(DATA, exist_ok=True)

issues = []      # data-quality notes (strings)
mismatches = []  # disagreements between sources (report vs clusters.json vs evidence vs library)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def split_name(key):
    m = re.match(r"^(.*?)\s*\((.*)\)\s*$", key)
    return (m.group(1), m.group(2)) if m else (key, None)


# ---------------------------------------------------------------- load evidence
evidence = OrderedDict()  # id -> row


def call_id(link):
    m = re.match(r"calls/([^/]+)/transcript\.md#(Q\d+)$", link)
    return f"call:{m.group(1)}:{m.group(2)}" if m else None


for fname, etype in (("call.jsonl", "founder_answer"), ("call-nonproblems.jsonl", "non_problem")):
    path = os.path.join(OUT, "evidence", fname)
    for ln, line in enumerate(read(path).splitlines(), 1):
        if not line.strip():
            continue
        r = json.loads(line)
        eid = call_id(r["link"])
        if eid is None:
            issues.append(f"{fname}:{ln} link not in calls/<slug>/transcript.md#Qn form: {r['link']}")
            eid = f"call:{fname}:{ln}"
        if eid in evidence:
            issues.append(f"duplicate evidence id {eid} ({fname}:{ln})")
            continue
        evidence[eid] = dict(id=eid, source=r["source"], author=r["author"], timestamp=r["timestamp"],
                             text=r["text"], link=r["link"], evidence_type=etype,
                             founder_words=1 if etype == "founder_answer" else 0,
                             file=f"evidence/{fname}")

lin = json.loads(read(os.path.join(OUT, "evidence", "linear-evidence.json")))
for r in lin:
    eid = r.get("id") or r["link"]
    if eid in evidence:
        issues.append(f"duplicate evidence id {eid} (linear)")
        continue
    evidence[eid] = dict(id=eid, source=r["source"], author=r["author"], timestamp=r["timestamp"],
                         text=r["text"], link=r["link"], evidence_type="founder_ticket",
                         founder_words=1, file="evidence/linear-evidence.json")

notion = json.loads(read(os.path.join(OUT, "evidence", "notion-evidence.json")))
for r in notion["items"]:
    eid = r["id"]
    counted = 1 if r["evidence_type"] == "founder_quote" else 0
    evidence[eid] = dict(id=eid, source=r["source"], author=r["author"], timestamp=r["timestamp"],
                         text=r["text"], link=r["link"], evidence_type=r["evidence_type"],
                         founder_words=counted, file="evidence/notion-evidence.json")

# ---------------------------------------------------------------- verify evidence against raw sources
transcripts = {}
layout_checks = OrderedDict()
for d in sorted(x for x in glob.glob(os.path.join(OUT, "calls", "*")) if os.path.isdir(x)):
    slug = os.path.basename(d)
    t = read(os.path.join(d, "transcript.md"))
    answers = re.findall(r"^A: (.*)$", t, flags=re.M)
    transcripts[slug] = {f"Q{i+1}": a for i, a in enumerate(answers)}
    transcripts[slug]["_header"] = t.splitlines()[0]

raw_checks = {"call_items_verbatim": 0, "linear_items_verbatim": 0, "notion_items_verbatim": 0, "failed": []}
tickets = {t["id"]: t for t in json.loads(read(os.path.join(UPLOADS, "linear", "tickets.json")))["tickets"]}
notion_page = read(os.path.join(UPLOADS, "notion", "office-hours-notes.md"))
for e in evidence.values():
    if e["source"] == "call":
        _, slug, q = e["id"].split(":")
        ok = transcripts.get(slug, {}).get(q) == e["text"]
        raw_checks["call_items_verbatim"] += ok
    elif e["source"] == "linear":
        t = tickets.get(e["link"])
        ok = bool(t) and e["text"] in t["description"] and t["reporter"] == e["author"] and t["created"] == e["timestamp"]
        raw_checks["linear_items_verbatim"] += ok
        if ok and e["text"] != t["description"]:
            issues.append(f"{e['id']}: evidence text is a verbatim excerpt, not the full ticket description "
                          f"(lead-in trimmed by the Linear scout, as its notes say)")
    else:
        ok = e["text"] in notion_page
        raw_checks["notion_items_verbatim"] += ok
    if not ok:
        raw_checks["failed"].append(e["id"])
        mismatches.append(f"evidence {e['id']} does not match its raw source verbatim")

# ---------------------------------------------------------------- clusters.json
cj = json.loads(read(os.path.join(OUT, "clusters.json")))
clusters = cj["clusters"]


def link_to_eid(link):
    if link.startswith("calls/"):
        return call_id(link)
    return link


# ---------------------------------------------------------------- pain library
library = {}
for p in sorted(glob.glob(os.path.join(LIB, "*.md"))):
    cid = os.path.basename(p)[:-3]
    if cid.startswith("_"):
        continue
    t = read(p)
    g = lambda k: (re.search(rf"^- {k}: (.*)$", t, flags=re.M) or [None, None])[1]
    hist = re.findall(r"^- (\d{4}-\d{2}-\d{2}) (\S+): (.*)$", t, flags=re.M)
    founders_sec = re.search(r"## Founders.*?\n(.*?)\n## ", t, flags=re.S).group(1)
    lib_links = re.findall(r"(?:call|linear|notion):(\S+?)(?:,|$)", founders_sec, flags=re.M)
    library[cid] = dict(distinct_founders=int(g("distinct_founders")),
                        first_seen=g("first_seen").split()[0], last_seen=g("last_seen").split()[0],
                        first_seen_run=re.search(r"run (\S+?)\)", g("first_seen")).group(1),
                        last_seen_run=re.search(r"run (\S+?)\)", g("last_seen")).group(1),
                        primitives=[x.strip() for x in g("primitives").split(",")],
                        kind=g("kind"), history=hist, links=[l.strip() for l in lib_links])
index_md = read(os.path.join(LIB, "_index.md"))

RUN_ID = cj["run_id"]

# ---------------------------------------------------------------- build DB
dbp = os.path.join(DATA, "room.db")
if os.path.exists(dbp):
    os.remove(dbp)
db = sqlite3.connect(dbp)
db.executescript("""
PRAGMA foreign_keys = ON;
CREATE TABLE evidence(
  id TEXT PRIMARY KEY, source TEXT NOT NULL, author TEXT NOT NULL, timestamp TEXT, text TEXT NOT NULL,
  link TEXT NOT NULL, evidence_type TEXT NOT NULL, founder_words INTEGER NOT NULL, file TEXT NOT NULL);
CREATE TABLE founders(
  founder_key TEXT PRIMARY KEY, name TEXT NOT NULL, company TEXT, sources TEXT NOT NULL,
  has_brief INTEGER NOT NULL, brief_path TEXT, stopped_or_paused INTEGER NOT NULL);
CREATE TABLE clusters(
  id TEXT PRIMARY KEY, rank INTEGER NOT NULL, name TEXT NOT NULL, kind TEXT NOT NULL, pain TEXT NOT NULL,
  primitive TEXT NOT NULL, first_seen TEXT, last_seen TEXT, founder_count INTEGER NOT NULL,
  stopped_count INTEGER NOT NULL, sources TEXT NOT NULL, fix_type TEXT NOT NULL, fix TEXT NOT NULL,
  status_vs_last_run TEXT NOT NULL, paraphrase_note TEXT, uncounted_support TEXT);
CREATE TABLE cluster_evidence(
  cluster_id TEXT NOT NULL REFERENCES clusters(id), evidence_id TEXT NOT NULL REFERENCES evidence(id),
  role TEXT NOT NULL, counts_toward_founders INTEGER NOT NULL, PRIMARY KEY(cluster_id, evidence_id));
CREATE TABLE cluster_founders(
  cluster_id TEXT NOT NULL REFERENCES clusters(id), founder_key TEXT NOT NULL REFERENCES founders(founder_key),
  stopped_or_paused INTEGER NOT NULL, PRIMARY KEY(cluster_id, founder_key));
CREATE TABLE cluster_primitives(
  cluster_id TEXT NOT NULL REFERENCES clusters(id), primitive TEXT NOT NULL, PRIMARY KEY(cluster_id, primitive));
CREATE TABLE primitive_founders(
  cluster_id TEXT NOT NULL REFERENCES clusters(id), primitive TEXT NOT NULL,
  founder_key TEXT NOT NULL REFERENCES founders(founder_key), PRIMARY KEY(cluster_id, primitive, founder_key));
CREATE TABLE quotes(
  id INTEGER PRIMARY KEY, cluster_id TEXT NOT NULL REFERENCES clusters(id),
  evidence_id TEXT NOT NULL REFERENCES evidence(id), seq INTEGER NOT NULL, author TEXT NOT NULL,
  source TEXT NOT NULL, link TEXT NOT NULL, text TEXT NOT NULL, verbatim_in_evidence INTEGER NOT NULL);
CREATE TABLE non_problems(
  founder_key TEXT NOT NULL REFERENCES founders(founder_key), topic TEXT NOT NULL, link TEXT NOT NULL,
  evidence_id TEXT REFERENCES evidence(id));
""")

for e in evidence.values():
    db.execute("INSERT INTO evidence VALUES (:id,:source,:author,:timestamp,:text,:link,:evidence_type,"
               ":founder_words,:file)", e)

# founders = distinct authors of counted (founder-worded) evidence
# Briefs: standard location briefs/<slug>.md (clusters.json "needs_briefs" map). Legacy copy calls/<slug>/needs-brief.md
# is checked for byte-identity. Transcript copies calls/<slug>.md are checked against calls/<slug>/transcript.md.
def rb(p):
    with open(p, "rb") as f:
        return f.read()


briefs = {}
brief_map = cj.get("needs_briefs") or {}
slugs = sorted(set(transcripts) | set(brief_map))
layout_checks["needs_briefs_map_in_clusters_json"] = bool(brief_map)
layout_checks["briefs"] = OrderedDict()
layout_checks["transcript_copies"] = OrderedDict()
for slug in slugs:
    rel = brief_map.get(slug, f"briefs/{slug}.md")
    std, legacy = os.path.join(OUT, rel), os.path.join(OUT, "calls", slug, "needs-brief.md")
    chk = OrderedDict(path=rel, exists=os.path.exists(std), in_map=slug in brief_map,
                      identical_to_legacy=(os.path.exists(std) and os.path.exists(legacy) and rb(std) == rb(legacy)))
    layout_checks["briefs"][slug] = chk
    if chk["exists"]:
        briefs[slug] = (read(std).splitlines()[0], rel)
        if not chk["identical_to_legacy"]:
            mismatches.append(f"brief {rel} differs from calls/{slug}/needs-brief.md")
    else:
        mismatches.append(f"brief for {slug} missing at {rel}")
    tc, td = os.path.join(OUT, "calls", f"{slug}.md"), os.path.join(OUT, "calls", slug, "transcript.md")
    ident = os.path.exists(tc) and os.path.exists(td) and rb(tc) == rb(td)
    layout_checks["transcript_copies"][slug] = OrderedDict(path=f"calls/{slug}.md", exists=os.path.exists(tc),
                                                           identical_to_calls_slug_transcript=ident)
    if os.path.exists(tc) and not ident:
        mismatches.append(f"calls/{slug}.md differs from calls/{slug}/transcript.md")

stopped_all = {f for c in clusters for f in c["stopped"]}
fsources = defaultdict(set)
fslug = {}
for e in evidence.values():
    if e["founder_words"] or e["evidence_type"] == "non_problem":
        fsources[e["author"]].add(e["source"])
    if e["source"] == "call":
        fslug[e["author"]] = e["id"].split(":")[1]
for fk in sorted(k for k in fsources if any(ev["author"] == k and ev["founder_words"] for ev in evidence.values())):
    name, company = split_name(fk)
    slug = fslug.get(fk)
    bpath = briefs.get(slug, (None, None))[1] if slug else None
    db.execute("INSERT INTO founders VALUES (?,?,?,?,?,?,?)",
               (fk, name, company, ",".join(sorted(fsources[fk])), 1 if bpath else 0, bpath,
                1 if fk in stopped_all else 0))
founder_keys = {r[0] for r in db.execute("SELECT founder_key FROM founders")}

# Ben: company label is the miner's descriptor, transcript header has no company
for slug, t in transcripts.items():
    hdr = t["_header"]
    for fk in founder_keys:
        if fslug.get(fk) == slug and fk not in hdr:
            issues.append(f"founder '{fk}': transcript header is '{hdr.lstrip('# ')}'. The company label is a "
                          f"descriptor added downstream, not a company name from the call")

uncounted_map = {u["id"]: u for u in cj["uncounted_evidence"]}

for c in clusters:
    lib = library.get(c["id"])
    if lib is None:
        mismatches.append(f"cluster {c['id']} has no pain-library file")
        first = last = None
        status = "unknown"
    else:
        first, last = lib["first_seen"], lib["last_seen"]
        created_this_run = lib["first_seen_run"] == RUN_ID and all(h[1] == RUN_ID for h in lib["history"])
        if created_this_run:
            status = "new"
        else:
            prev = [h for h in lib["history"] if h[1] != RUN_ID]
            m = re.search(r"(\d+) founder", prev[-1][2]) if prev else None
            prev_n = int(m.group(1)) if m else None
            status = "growing" if prev_n is not None and c["founder_count"] > prev_n else "unchanged"
        if lib["distinct_founders"] != c["founder_count"]:
            mismatches.append(f"{c['id']}: library founders {lib['distinct_founders']} vs clusters.json {c['founder_count']}")
        if set(lib["primitives"]) != set(c["primitives"]):
            mismatches.append(f"{c['id']}: library primitives differ from clusters.json")
    db.execute("INSERT INTO clusters VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (c["id"], c["rank"], c["name"], c["kind"], c["pain"], ", ".join(c["primitives"]), first, last,
                c["founder_count"], len(c["stopped"]), ",".join(c["sources"]), c["fix_type"], c["fix"], status,
                c["paraphrase_note"], c["uncounted_support"]))
    for p in c["primitives"]:
        db.execute("INSERT INTO cluster_primitives VALUES (?,?)", (c["id"], p))
    for p, fl in c["primitive_founders"].items():
        for f in fl:
            db.execute("INSERT INTO primitive_founders VALUES (?,?,?)", (c["id"], p, f))
    # evidence links
    linked = []
    for l in c["evidence_links"]:
        eid = link_to_eid(l)
        if eid not in evidence:
            mismatches.append(f"{c['id']}: evidence link {l} not found in evidence files")
            continue
        linked.append(eid)
    quoted = set()
    for i, q in enumerate(c["quotes"], 1):
        eid = link_to_eid(q["link"])
        if eid not in evidence:
            eid = f"call:{call_id(q['link'])}" if q["link"].startswith("calls/") else eid
        ev = evidence.get(eid)
        ok = int(bool(ev) and q["text"] in ev["text"] and ev["author"] == q["author"] and ev["source"] == q["source"])
        if not ok:
            mismatches.append(f"{c['id']} quote {i} not a verbatim substring of {q['link']} (or author/source differ)")
        if ev and not ev["founder_words"]:
            mismatches.append(f"{c['id']} quote {i} comes from uncounted evidence {eid}")
        if eid not in linked:
            mismatches.append(f"{c['id']} quote {i} link {q['link']} missing from evidence_links")
        quoted.add(eid)
        db.execute("INSERT INTO quotes(cluster_id,evidence_id,seq,author,source,link,text,verbatim_in_evidence) "
                   "VALUES (?,?,?,?,?,?,?,?)", (c["id"], eid, i, q["author"], q["source"], q["link"], q["text"], ok))
    for eid in linked:
        role = "quoted" if eid in quoted else "linked"
        db.execute("INSERT INTO cluster_evidence VALUES (?,?,?,?)",
                   (c["id"], eid, role, evidence[eid]["founder_words"]))
    for uid, u in uncounted_map.items():
        if u["attached_to"] == c["id"]:
            db.execute("INSERT INTO cluster_evidence VALUES (?,?,?,0)", (c["id"], uid, "context_uncounted"))
    # founders derived from counted linked evidence
    derived = {evidence[e]["author"] for e in linked if evidence[e]["founder_words"]}
    if derived != set(c["founders"]):
        mismatches.append(f"{c['id']}: founders from linked evidence {sorted(derived)} vs clusters.json {c['founders']}")
    if len(set(c["founders"])) != c["founder_count"]:
        mismatches.append(f"{c['id']}: founder_count {c['founder_count']} != len(founders) {len(set(c['founders']))}")
    dsrc = sorted({evidence[e]["source"] for e in linked if evidence[e]["founder_words"]})
    if dsrc != sorted(c["sources"]):
        mismatches.append(f"{c['id']}: sources from evidence {dsrc} vs clusters.json {c['sources']}")
    for f in c["founders"]:
        if f not in founder_keys:
            mismatches.append(f"{c['id']}: founder {f} not in founders table")
        db.execute("INSERT INTO cluster_founders VALUES (?,?,?)", (c["id"], f, 1 if f in c["stopped"] else 0))
    # library founder links vs clusters.json links
    if lib:
        libl = {link_to_eid(x) for x in lib["links"]}
        if libl != set(linked):
            mismatches.append(f"{c['id']}: pain-library evidence links {sorted(libl)} vs clusters.json {sorted(linked)}")

for n in cj["explicit_non_problems"]:
    eid = call_id(n["link"])
    db.execute("INSERT INTO non_problems VALUES (?,?,?,?)", (n["founder"], n["topic"], n["link"],
                                                            eid if eid in evidence else None))
db.commit()

# ---------------------------------------------------------------- metrics (SQL over the DB)
q = lambda sql, *a: db.execute(sql, a).fetchall()
one = lambda sql, *a: db.execute(sql, a).fetchone()[0]

n_founders = one("SELECT COUNT(*) FROM founders")
if n_founders != cj["distinct_founders_total"]:
    mismatches.append(f"distinct founders: db {n_founders} vs clusters.json {cj['distinct_founders_total']}")
n_founders_in_clusters = one("SELECT COUNT(DISTINCT founder_key) FROM cluster_founders")
blocker_ids = [r[0] for r in q("SELECT id FROM clusters WHERE kind='blocker'")]

# primitive tally recomputed from primitive_founders over blocker clusters
tally = []
for p in [t["primitive"] for t in cj["primitive_tally"]]:
    fl = sorted(r[0] for r in q("SELECT DISTINCT pf.founder_key FROM primitive_founders pf JOIN clusters c "
                                "ON c.id=pf.cluster_id WHERE c.kind='blocker' AND pf.primitive=?", p))
    st = sorted(r[0] for r in q("SELECT DISTINCT pf.founder_key FROM primitive_founders pf JOIN clusters c "
                                "ON c.id=pf.cluster_id JOIN cluster_founders cf ON cf.cluster_id=pf.cluster_id "
                                "AND cf.founder_key=pf.founder_key WHERE c.kind='blocker' AND pf.primitive=? "
                                "AND cf.stopped_or_paused=1", p))
    ranks = sorted(r[0] for r in q("SELECT DISTINCT c.rank FROM primitive_founders pf JOIN clusters c ON "
                                   "c.id=pf.cluster_id WHERE c.kind='blocker' AND pf.primitive=?", p))
    tally.append(OrderedDict(primitive=p, distinct_founders_blocked=len(fl), founders_stopped=len(st),
                             cluster_ranks=ranks, founders=fl, founders_stopped_list=st))
for mine, theirs in zip(tally, cj["primitive_tally"]):
    for k in ("distinct_founders_blocked", "founders_stopped", "cluster_ranks"):
        if mine[k] != theirs[k]:
            mismatches.append(f"primitive tally {mine['primitive']}.{k}: recomputed {mine[k]} vs clusters.json {theirs[k]}")
    if mine["founders"] != sorted(theirs["founders"]):
        mismatches.append(f"primitive tally {mine['primitive']} founders differ")
# requirement cluster primitives (reported separately)
req = [dict(cluster_id=r[0], rank=r[1], primitives=r[2].split(", "), founder_count=r[3])
       for r in q("SELECT id, rank, primitive, founder_count FROM clusters WHERE kind='requirement' ORDER BY rank")]

# evidence per source
ev_by_source = OrderedDict()
for src in ("call", "linear", "notion"):
    rows = q("SELECT evidence_type, COUNT(*) FROM evidence WHERE source=? GROUP BY evidence_type ORDER BY 1", src)
    ev_by_source[src] = OrderedDict(
        total=sum(r[1] for r in rows),
        founder_words=one("SELECT COUNT(*) FROM evidence WHERE source=? AND founder_words=1", src),
        linked_to_a_cluster=one("SELECT COUNT(DISTINCT ce.evidence_id) FROM cluster_evidence ce JOIN evidence e ON "
                                "e.id=ce.evidence_id WHERE e.source=? AND ce.counts_toward_founders=1", src),
        with_timestamp=one("SELECT COUNT(*) FROM evidence WHERE source=? AND timestamp IS NOT NULL", src),
        by_type=OrderedDict(rows),
        files=sorted(r[0] for r in q("SELECT DISTINCT file FROM evidence WHERE source=?", src)))

pains_by_source = OrderedDict()
for src in ("call", "linear", "notion"):
    cl = [r[0] for r in q("SELECT DISTINCT ce.cluster_id FROM cluster_evidence ce JOIN evidence e ON "
                          "e.id=ce.evidence_id JOIN clusters c ON c.id=ce.cluster_id WHERE e.source=? AND "
                          "ce.counts_toward_founders=1 ORDER BY c.rank", src)]
    only = [c for c in cl if one("SELECT COUNT(DISTINCT e.source) FROM cluster_evidence ce JOIN evidence e ON "
                                 "e.id=ce.evidence_id WHERE ce.cluster_id=? AND ce.counts_toward_founders=1", c) == 1]
    pains_by_source[src] = OrderedDict(
        clusters=len(cl), blocker_clusters=sum(1 for c in cl if c in blocker_ids),
        clusters_only_from_this_source=len(only), founders=one("SELECT COUNT(*) FROM founders WHERE sources LIKE ?", f"%{src}%"),
        quotes=one("SELECT COUNT(*) FROM quotes WHERE source=?", src), cluster_ids=cl)

multi_source = one("SELECT COUNT(*) FROM clusters WHERE sources LIKE '%,%'")

clusters_out = []
for r in q("SELECT id, rank, name, kind, pain, primitive, first_seen, last_seen, founder_count, stopped_count, "
           "sources, fix_type, fix, status_vs_last_run, paraphrase_note, uncounted_support FROM clusters ORDER BY rank"):
    cid = r[0]
    clusters_out.append(OrderedDict(
        rank=r[1], id=cid, name=r[2], kind=r[3], pain=r[4], primitives=r[5].split(", "),
        founder_count=r[8], founders=[x[0] for x in q("SELECT founder_key FROM cluster_founders WHERE cluster_id=? ORDER BY rowid", cid)],
        stopped_count=r[9], stopped=[x[0] for x in q("SELECT founder_key FROM cluster_founders WHERE cluster_id=? AND stopped_or_paused=1 ORDER BY rowid", cid)],
        sources=r[10].split(","), fix_type=r[11], fix=r[12], first_seen=r[6], last_seen=r[7],
        status_vs_last_run=r[13], evidence_items_founder_words=one("SELECT COUNT(*) FROM cluster_evidence WHERE cluster_id=? AND counts_toward_founders=1", cid),
        uncounted_context=[x[0] for x in q("SELECT evidence_id FROM cluster_evidence WHERE cluster_id=? AND counts_toward_founders=0", cid)],
        paraphrase_note=r[14], uncounted_support=r[15],
        quotes=[OrderedDict(text=x[0], author=x[1], source=x[2], link=x[3], evidence_id=x[4], verbatim=bool(x[5]))
                for x in q("SELECT text, author, source, link, evidence_id, verbatim_in_evidence FROM quotes WHERE cluster_id=? ORDER BY seq", cid)]))

status_counts = OrderedDict((s, one("SELECT COUNT(*) FROM clusters WHERE status_vs_last_run=?", s))
                            for s in ("new", "growing", "unchanged"))

founders_out = [OrderedDict(founder=r[0], name=r[1], company=r[2], sources=r[3].split(","), has_brief=bool(r[4]),
                            brief_path=r[5], stopped_or_paused=bool(r[6]),
                            clusters=[x[0] for x in q("SELECT c.rank FROM cluster_founders cf JOIN clusters c ON c.id=cf.cluster_id WHERE cf.founder_key=? ORDER BY c.rank", r[0])])
                for r in q("SELECT founder_key, name, company, sources, has_brief, brief_path, stopped_or_paused FROM founders ORDER BY has_brief DESC, founder_key")]

unlinked = [OrderedDict(id=r[0], author=r[1], link=r[2]) for r in q(
    "SELECT id, author, link FROM evidence WHERE founder_words=1 AND id NOT IN "
    "(SELECT evidence_id FROM cluster_evidence) ORDER BY id")]
uncounted = [OrderedDict(id=r[0], evidence_type=r[1], author=r[2], text=r[3],
                         attached_to=uncounted_map.get(r[0], {}).get("attached_to"))
             for r in q("SELECT id, evidence_type, author, text FROM evidence WHERE founder_words=0 "
                        "AND evidence_type!='non_problem' ORDER BY id")]
nonprob = [OrderedDict(founder=r[0], topic=r[1], link=r[2], evidence_id=r[3],
                       evidence_file=one("SELECT file FROM evidence WHERE id=?", r[3]) if r[3] else None)
           for r in q("SELECT founder_key, topic, link, evidence_id FROM non_problems")]
for n in nonprob:
    if n["evidence_file"] != "evidence/call-nonproblems.jsonl":
        issues.append(f"non-problem {n['founder']} ({n['link']}) is stored in {n['evidence_file']}, "
                      f"not in evidence/call-nonproblems.jsonl, which holds only Tomas Q5")

# report cross-check: parse the "Ranked clusters at a glance" and primitive tables
rep = read(os.path.join(OUT, "room-report.md"))
m = re.search(r"\*\*(\d+) distinct founders\*\* · (\d+) clusters", rep)
report_checks = OrderedDict()
report_checks["distinct_founders"] = int(m.group(1))
report_checks["clusters"] = int(m.group(2))
if int(m.group(1)) != n_founders: mismatches.append("report distinct founders != db")
if int(m.group(2)) != len(clusters_out): mismatches.append("report cluster count != db")
glance = re.findall(r"^\| (\d+) \| (.+?) \| (\d+) \| (\d+) \| (.+?) \| (.+?) \| (.+?) \|$", rep, flags=re.M)
report_checks["glance_rows"] = len(glance)
for row in glance:
    rk = int(row[0]); c = clusters_out[rk - 1]
    nm = row[1].replace(" *(requirement)*", "")
    exp = (c["name"], c["founder_count"], c["stopped_count"], ", ".join(c["sources"]), ", ".join(c["primitives"]), c["fix_type"])
    got = (nm, int(row[2]), int(row[3]), row[4], row[5], row[6])
    if exp != got:
        mismatches.append(f"report glance row {rk} {got} vs clusters.json {exp}")
ptab = re.findall(r"^\| ([a-zA-Z ]+?) \| (\d+) \| (\d+) \| ([\d, ]+|—) \|$", rep, flags=re.M)
report_checks["primitive_rows"] = len(ptab)
_sec = re.search(r"^## Blocker tally by CMA primitive", rep, flags=re.M)
report_checks["primitive_tally_section_line"] = rep[:_sec.start()].count("\n") + 1 if _sec else None
report_checks["primitive_tally_section_is_last"] = bool(_sec) and "\n## " not in rep[_sec.end():]
if len(ptab) != len(tally):
    mismatches.append(f"report primitive table has {len(ptab)} rows, recomputed tally has {len(tally)}")
tmap = {t["primitive"]: t for t in tally}
for p, a, b, rks in ptab:
    t = tmap.get(p)
    rl = [] if rks == "—" else [int(x) for x in rks.split(",")]
    if not t or (t["distinct_founders_blocked"], t["founders_stopped"], t["cluster_ranks"]) != (int(a), int(b), rl):
        mismatches.append(f"report primitive row {p} ({a},{b},{rks}) vs recomputed {t and (t['distinct_founders_blocked'], t['founders_stopped'], t['cluster_ranks'])}")
# per-cluster "Distinct founders: N" headers
for rk, n in re.findall(r"^### (\d+)\. .*?\n\n\*\*Distinct founders: (\d+)\*\*", rep, flags=re.M | re.S):
    if clusters_out[int(rk) - 1]["founder_count"] != int(n):
        mismatches.append(f"report cluster {rk} header founders {n} mismatch")
# every blockquote in report must be verbatim in some evidence item
bq = []
for block in re.findall(r"((?:^ *>(?: .*)?\n)+)", rep, flags=re.M):
    lines = [l.strip()[2:] for l in block.splitlines() if l.strip().startswith("> ")]
    lines = [l for l in lines if not l.startswith("— ")]
    if lines:
        bq.append(" ".join(lines).strip())
all_text = [e["text"] for e in evidence.values()]
bad = [b for b in bq if not any(b in t for t in all_text)]
report_checks["report_blockquotes"] = len(bq)
report_checks["report_blockquotes_verbatim"] = len(bq) - len(bad)
for b in bad:
    mismatches.append(f"report quote not verbatim in any evidence: {b[:80]}")
# per-cluster report quotes must equal clusters.json quotes (text, order, author, link)
secs = re.split(r"^### (\d+)\. ", rep, flags=re.M)
same = 0
for i in range(1, len(secs), 2):
    rk = int(secs[i]); body = secs[i + 1].split("\n## ")[0]
    got = []
    for block in re.findall(r"((?:^>.*\n)+)", body, flags=re.M):
        ls = [l[2:] for l in block.splitlines() if l.startswith("> ")]
        got.append((" ".join(l for l in ls if not l.startswith("— ")),
                    next((l for l in ls if l.startswith("— ")), "")))
    c = clusters_out[rk - 1]
    if [g[0] for g in got] == [x["text"] for x in c["quotes"]] and all(
            x["author"] in g[1] and x["link"] in g[1] for x, g in zip(c["quotes"], got)):
        same += 1
    else:
        mismatches.append(f"report cluster {rk} quotes differ from clusters.json (text/order/attribution)")
report_checks["clusters_with_identical_quotes_in_report_and_json"] = same
m = re.search(r"(\w+) of the ten founders stopped", rep)
report_checks["stopped_sentence"] = m.group(1) if m else None
n_stopped = one("SELECT COUNT(*) FROM founders WHERE stopped_or_paused=1")
if m and {"Four": 4}.get(m.group(1)) != n_stopped:
    mismatches.append("report 'N of the ten founders stopped' vs db")

# library index cross-check
for cid, n in re.findall(r"^\| ([a-z-]+) \| (\d+) \|", index_md, flags=re.M):
    c = next((x for x in clusters_out if x["id"] == cid), None)
    if not c or c["founder_count"] != int(n):
        mismatches.append(f"pain-library _index {cid}={n} vs clusters.json")

dates = [r[0] for r in q("SELECT timestamp FROM evidence WHERE timestamp IS NOT NULL ORDER BY 1")]
table_rows = OrderedDict((t, one(f"SELECT COUNT(*) FROM {t}")) for t in
                         [r[0] for r in q("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")])

metrics = OrderedDict(
    run_id=RUN_ID, mode=cj["mode"], generated=cj["generated"],
    sources_of_truth=["room-report.md", "clusters.json", "evidence/*", "briefs/*.md", "calls/*/transcript.md",
                      "/mnt/memory/room-miner-pain-library/*.md"],
    headline=OrderedDict(
        distinct_founders=n_founders,
        clusters=len(clusters_out),
        blocker_clusters=len(blocker_ids),
        requirement_clusters=len(clusters_out) - len(blocker_ids),
        founders_stopped_or_paused=n_stopped,
        multi_founder_clusters=one("SELECT COUNT(*) FROM clusters WHERE founder_count>=2"),
        multi_source_clusters=multi_source,
        top_cluster_founders=clusters_out[0]["founder_count"],
        evidence_items_total=one("SELECT COUNT(*) FROM evidence"),
        evidence_items_founder_words=one("SELECT COUNT(*) FROM evidence WHERE founder_words=1"),
        evidence_items_not_founder_words=one("SELECT COUNT(*) FROM evidence WHERE founder_words=0"),
        quotes_in_clusters=one("SELECT COUNT(*) FROM quotes"),
        quotes_verbatim=one("SELECT COUNT(*) FROM quotes WHERE verbatim_in_evidence=1"),
        source_types=len(ev_by_source)),
    clusters=clusters_out,
    founders_per_cluster=[OrderedDict(rank=c["rank"], id=c["id"], name=c["name"], kind=c["kind"],
                                      founders=c["founder_count"], stopped=c["stopped_count"]) for c in clusters_out],
    pains_by_primitive=OrderedDict(
        note="Blocker clusters only (requirement cluster excluded). A founder counts once per primitive, and only "
             "where their own evidence implicates it (clusters.json primitive_founders).",
        tally=tally, requirement_clusters=req),
    pains_by_source=pains_by_source,
    evidence_by_source=ev_by_source,
    cluster_status_vs_last_run=OrderedDict(
        counts=status_counts,
        basis="Pain-library history. Every cluster file was created in this run (first_seen = last_seen = "
              + RUN_ID + ") and the miner's journal says the library was empty at the start, so there is no "
              "earlier run to compare against. Every cluster counts as new."),
    founders=founders_out,
    coverage=OrderedDict(
        founders_with_brief=one("SELECT COUNT(*) FROM founders WHERE has_brief=1"),
        founders_without_brief=one("SELECT COUNT(*) FROM founders WHERE has_brief=0"),
        founders_total=n_founders,
        founders_in_at_least_one_cluster=n_founders_in_clusters,
        sources_with_zero_items=[s for s, v in ev_by_source.items() if v["total"] == 0],
        founder_evidence_not_linked_to_any_cluster=unlinked,
        uncounted_evidence=uncounted,
        explicit_non_problems=nonprob,
        items_with_timestamp=len(dates),
        items_without_timestamp=one("SELECT COUNT(*) FROM evidence WHERE timestamp IS NULL"),
        timestamp_range=[dates[0][:10], dates[-1][:10]] if dates else None),
    verification=OrderedDict(
        evidence_vs_raw_sources=raw_checks,
        file_layout=layout_checks,
        report_checks=report_checks,
        mismatches=mismatches,
        data_quality_notes=issues),
    table_rows=table_rows)

with open(os.path.join(DATA, "metrics.json"), "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=1, ensure_ascii=False)
db.close()
print(json.dumps(OrderedDict(table_rows=table_rows, headline=metrics["headline"], mismatches=mismatches,
                             issues=issues, raw=raw_checks, report=report_checks, status=status_counts), indent=1))
