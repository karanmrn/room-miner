# Room sweep: definition of done

1. `/mnt/session/outputs/digest.md` exists and leads with clusters that are new or grew since the last run; unchanged clusters appear in one line. If nothing new arrived, the digest says so plainly in its first line.
2. Every quoted string in the digest appears character for character in an evidence item under `/mnt/session/outputs/evidence/`.
3. The pain-library memory store reflects the updated clusters (counts and last-seen).
4. `/mnt/session/outputs/run-manifest.json` has a `done` entry with existing outputs for every numbered step; `dashboard.html` numbers all appear in `data/metrics.json`.
5. A new run-journal entry records this run.
