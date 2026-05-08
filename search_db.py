"""
search_db.py

Performs semantic search over the papers table.
Takes a query in plain English, embeds it, and returns the
top-k most similar papers using vector similarity.

Run with: python search_db.py
"""

import os
import psycopg
from google import genai

from config import DB_URL, EMBEDDING_MODEL

# -- Gemini setup --    
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

gemini_client = genai.Client(api_key=api_key)

# -- User query config --
# Change the query for different search terms
QUERY = "papers on large language models safety?"
TOP_K = 5  # Number of results to return

# -- Embed the query --
print(f"Query: {QUERY}\n")
print("Embedding the query...")

response = gemini_client.models.embed_content(
    model=EMBEDDING_MODEL,
    contents=QUERY,
)
query_embedding = list(response.embeddings[0].values)

# -- Search the database --
# pgvector exposes distance operators between vectors:
#   <->  Euclidean distance
#   <#>  negative inner product
#   <=>  cosine distance (1 - cosine similarity)
#
# Cosine distance is the standard choice for text embeddings.
# Smaller distance = more similar.
#
# We ORDER BY the distance and LIMIT to the top K results.
SEARCH_SQL = """
SELECT
    arxiv_id,
    title,
    category_label,
    published,
    embedding <=> %s::vector AS distance
FROM papers
ORDER BY embedding <=> %s::vector
LIMIT %s;
"""

print(f"Searching for top {TOP_K} matches...\n")

with psycopg.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        cur.execute(SEARCH_SQL, (query_embedding, query_embedding, TOP_K))
        results = cur.fetchall()

# ── Show results ───────────────────────────────────────────────────────────────
print("=" * 70)
for i, (arxiv_id, title, category, published, distance) in enumerate(results, 1):
    similarity = 1 - distance   # turn cosine distance back into similarity
    print(f"\n{i}. {title}")
    print(f"   arXiv ID:    {arxiv_id}")
    print(f"   Category:    {category}")
    print(f"   Published:   {published}")
    print(f"   Similarity:  {similarity:.4f}")
