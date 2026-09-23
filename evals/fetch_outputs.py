"""Download all output files of a session and rebuild the folder layout.

The Files API keeps only bare filenames (no directories), so four transcript.md files
collide. Every file is saved under files/<file_id>-<name>, then sorted back into
calls/<slug>.md, briefs/<slug>.md, evidence/*.jsonl and the top level by content.

    python3 evals/fetch_outputs.py <session_id>
"""
import json, pathlib, re, shutil, sys, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY = next(l.split("=", 1)[1].strip() for l in (ROOT / ".env").read_text().splitlines() if l.startswith("ANTHROPIC_API_KEY="))
H = {"x-api-key": KEY, "anthropic-version": "2023-06-01", "anthropic-beta": "managed-agents-2026-04-01"}
# founder slug -> strings that identify their transcript or brief
FOUNDERS = {"priya": ["Priya", "Lumen"], "tomas": ["Tomás", "Tomas", "Patchwork"],
            "aisha": ["Aisha", "Ledgerline"], "ben": ["Ben", "newsletter", "climate"], "karan": ["karan", "Karan"]}


def req(path):
    r = urllib.request.Request("https://api.anthropic.com/v1" + path)
    for k, v in H.items():
        r.add_header(k, v)
    return urllib.request.urlopen(r, timeout=120).read()


def main(sid):
    out = ROOT / "runs" / sid
    raw = out / "files"
    raw.mkdir(parents=True, exist_ok=True)
    files, page = [], None
    while True:
        d = json.loads(req(f"/files?scope_id={sid}&limit=100" + (f"&page={urllib.parse.quote(page)}" if page else "")))
        files += d["data"]
        page = d.get("next_page") if d.get("has_more") else None
        if not page:
            break
    skipped = []
    for f in files:
        p = raw / f"{f['id']}-{f['filename']}"
        if p.exists():
            continue
        if not f.get("downloadable", True):
            skipped.append(f"{f['filename']} (not downloadable)")
            continue
        try:
            p.write_bytes(req(f"/files/{f['id']}/content"))
        except urllib.error.HTTPError as e:
            skipped.append(f"{f['filename']} (HTTP {e.code}: {e.read()[:120]!r})")
    if skipped:
        print("   skipped: " + "; ".join(skipped))
    print(f"⬇️  {len(files)} files → {raw.relative_to(ROOT)}")

    def slug_of(text):
        head = text[:1500]
        hits = {s: sum(head.count(k) for k in keys) for s, keys in FOUNDERS.items()}
        best = max(hits, key=hits.get)
        return best if hits[best] else None

    for sub in ("calls", "briefs", "evidence", "data"):
        (out / sub).mkdir(exist_ok=True)
    for p in sorted(raw.iterdir()):
        name = p.name.split("-", 1)[1]
        text = p.read_text(errors="replace")
        stem = pathlib.Path(name).stem
        if name.endswith((".jsonl", ".json")) and ("evidence" in name or name in ("call.jsonl", "linear.jsonl", "notion.jsonl")):
            src = "call" if "call" in name else "linear" if "linear" in name else "notion" if "notion" in name else stem
            dest = out / "evidence" / f"{src}.jsonl"
            if name.endswith(".json") and text.lstrip().startswith("["):  # JSON array -> JSONL
                text = "\n".join(json.dumps(x) for x in json.loads(text)) + "\n"
            dest.write_text(text)
        elif re.search(r"brief", name, re.I) or re.search(r"(?im)^#+.*\buse_case\b|\*\*use_case", text):
            s = slug_of(text) or stem
            (out / "briefs" / f"{s}.md").write_text(text)
        elif re.search(r"transcript", name, re.I) or re.search(r"(?m)^Q\d*:", text) or stem in FOUNDERS:
            s = stem if stem in FOUNDERS else slug_of(text) or stem
            (out / "calls" / f"{s}.md").write_text(text)
        elif name in ("metrics.json", "room.db", "README.md") or name.endswith(".db"):
            shutil.copy(p, out / "data" / name)
        else:
            shutil.copy(p, out / name)
    for sub in ("calls", "briefs", "evidence", "data"):
        print(f"   {sub}/: {', '.join(sorted(x.name for x in (out / sub).iterdir())) or '-'}")
    print("   top: " + ", ".join(sorted(x.name for x in out.iterdir() if x.is_file())))


if __name__ == "__main__":
    main(sys.argv[1])
