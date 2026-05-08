"""
embed_papers.py

Second step of the ingestion pipeline.
Fetches papers from arXiv, generates an embedding for each abstract
using the Gemini API, and saves results to a JSON file.

Imports category list and settings from config.py — do not hardcode
categories or model names in this file.

Run with: python embed_papers.py
"""

import os
import json
import arxiv
from dotenv import load_dotenv
from google import genai

# Import shared configuration
from config import (
    ARXIV_CATEGORIES,
    EMBEDDING_MODEL,
    DEFAULT_MAX_RESULTS,
    DEFAULT_DELAY_SECONDS,
    DEFAULT_NUM_RETRIES,
    DEFAULT_OUTPUT_FILE,
)

# ── Load environment variables ─────────────────────────────────────────────────
load_dotenv()

# ── Configure Gemini client ────────────────────────────────────────────────────
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found. "
        "Make sure your .env file exists and contains GEMINI_API_KEY=your-key"
    )

# Named gemini_client (not just "client") to avoid conflict with arxiv_client below
gemini_client = genai.Client(api_key=api_key)

# ── Choose a category ──────────────────────────────────────────────────────────
SELECTED_CATEGORY_LABEL = "Machine Learning"  # Change this to fetch a different category
CATEGORY = ARXIV_CATEGORIES[SELECTED_CATEGORY_LABEL]

# ── Fetch papers from arXiv ────────────────────────────────────────────────────
print(f"Fetching {DEFAULT_MAX_RESULTS} papers from arXiv")
print(f"Category: {SELECTED_CATEGORY_LABEL} ({CATEGORY})")
print("=" * 60)

search = arxiv.Search(
    query=f"cat:{CATEGORY}",
    max_results=DEFAULT_MAX_RESULTS,
    sort_by=arxiv.SortCriterion.SubmittedDate,
    sort_order=arxiv.SortOrder.Descending,
)

# Named arxiv_client to keep it distinct from gemini_client
arxiv_client = arxiv.Client(
    page_size=100,
    delay_seconds=DEFAULT_DELAY_SECONDS,
    num_retries=DEFAULT_NUM_RETRIES,
)

papers = list(arxiv_client.results(search))
print(f"Fetched {len(papers)} papers\n")

# ── Generate embeddings and collect results ────────────────────────────────────
print("Generating embeddings...")
print("-" * 60)

output = []

for i, paper in enumerate(papers, start=1):

    # Combine title and abstract for richer embedding
    text_to_embed = f"Title: {paper.title}\n\nAbstract: {paper.summary}"

    # Call the Gemini embedding API
    response = gemini_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text_to_embed,
    )

    # Extract the embedding vector from the response
    embedding = response.embeddings[0].values

    # Print progress
    print(f"\n{i}. {paper.title[:80]}...")
    print(f"   arXiv ID:         {paper.entry_id.split('/')[-1]}")
    print(f"   Embedding length: {len(embedding)} dimensions")
    print(f"   First 5 values:   {[round(v, 4) for v in embedding[:5]]}")

    # Collect everything for saving
    output.append({
        "arxiv_id": paper.entry_id.split("/")[-1],
        "title": paper.title,
        "authors": [a.name for a in paper.authors],
        "published": str(paper.published.date()),
        "category_label": SELECTED_CATEGORY_LABEL,
        "category_code": CATEGORY,
        "abstract": paper.summary,
        "embedding": list(embedding),  # convert to plain list for JSON serialisation
    })

# ── Save to JSON ───────────────────────────────────────────────────────────────
with open(DEFAULT_OUTPUT_FILE, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n{'=' * 60}")
print(f"Saved {len(output)} papers with embeddings to {DEFAULT_OUTPUT_FILE}")