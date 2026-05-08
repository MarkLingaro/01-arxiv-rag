"""
app/database.py

Database helpers.
"""
import psycopg
from config import DB_URL

# -- DB SQL creation and search queries --

SEARCH_SQL = """
WITH scored AS (
    SELECT
        arxiv_id,
        title,
        authors,
        published,
        category_label,
        abstract,
        embedding <=> %s::vector AS distance
    FROM papers
)
SELECT *
FROM scored
ORDER BY distance
LIMIT %s;
"""
# -- Search helper function --
def search_papers(query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """
    Run semantic search. Returns a list of papers as dicts, ranked by
    similarity to the query embedding.
    """
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SEARCH_SQL, (query_embedding, top_k))
            rows = cur.fetchall()

    # Convert raw tuples into dicts with named keys.
    # Easier for callers (and for FastAPI's JSON serializer) to work with.
    results = []
    for arxiv_id, title, authors, published, category, abstract, distance in rows:
        results.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors,
            "published": str(published),
            "category_label": category,
            "abstract": abstract,
            "similarity": 1 - distance,
        })

    return results