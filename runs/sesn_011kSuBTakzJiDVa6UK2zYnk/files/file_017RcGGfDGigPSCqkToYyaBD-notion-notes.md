# Notion scout notes: source quirks

- Page read: `/mnt/session/uploads/notion/office-hours-notes.md` (1 page). Read-only; nothing was written back to Notion.
- **There are no dates anywhere on the page.** No session dates and no page timestamps, so every item has `timestamp: null`.
- The page is labelled "Seeded demo content (mock Notion export for v0)", so treat it as demo data.
- Mentors wrote the notes. Only text in quotation marks counts as the founder's own words. The two kinds of text are marked like this:
  - `founder_quote`: a line prefixed "Quote:", or an "Also mentioned:" line whose text is in quotation marks. The quotation marks are kept in `text`.
  - `note_taker_paraphrase`: an unquoted bullet in a founder's session that describes their problem. It is attributed to the founder, but the words are the mentor's.
  - `mentor_observation`: a bullet under "Mentor takeaways". Author is "mentor notes". These are aggregates across teams that aren't named, so they should not add to founder counts.
- Bullets that only give context ("Building a …") are not pain. They are stored in the `context` field, not as separate items.
- No instructions were embedded in the page content.
- Memory: `/mnt/memory/scout-lessons/` (the path in my standing instructions) does not exist, and `/mnt/memory/` came back empty. No scout lessons were available.
- Output path: my standing instructions say `evidence/notion.jsonl`, but this dispatch asked for `evidence/notion-evidence.json`. I wrote to the dispatch path only.
