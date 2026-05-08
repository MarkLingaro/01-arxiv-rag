"""
load_to_db.py

Reads papers_with_embeddings.json (created by embed_papers.py)
and inserts the rows into the 'papers' table.

If a paper already exists (same arxiv_id), it is skipped.

Run with: python load_to_db.py
"""

import json
import psycopg
from config import DB_URL, DEFAULT_OUTPUT_FILE

# -- Load papers from JSON --
print(f"Reading papers from {DEFAULT_OUTPUT_FILE}...")

with open(DEFAULT_OUTPUT_FILE, "r") as f:
    papers = json.load(f)

print(f"Found {len(papers)} papers to insert.\n")

# --Insert in DB --
# ON CONFLICT (arxiv_id) DO NOTHING means: if a paper with this arxiv_id
# already exists, skip it silently. Lets you re-run safely.

INSERT_SQL = """
INSERT INTO papers (
    arxiv_id, title, authors, published,
    category_label, category_code, abstract, embedding
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (arxiv_id) DO NOTHING;
"""

inserted = 0
skipped = 0

with psycopg.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        for paper in papers:
            cur.execute(
                INSERT_SQL,
                (
                    paper["arxiv_id"],
                    paper["title"],
                    paper["authors"],
                    paper["published"],
                    paper["category_label"],
                    paper["category_code"],
                    paper["abstract"],
                    paper["embedding"],
                ),
            )
            # cur.rowcount is 1 if a row was inserted, 0 if it was a conflict
            if cur.rowcount == 1:
                inserted += 1
            else:
                skipped += 1

    conn.commit()

print(f"Inserted: {inserted} new papers")
print(f"Skipped (already in DB): {skipped} papers")

# ── Verify ─────────────────────────────────────────────────────────────────────
with psycopg.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM papers")
        total = cur.fetchone()[0]
        print(f"Total papers in database: {total}")