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
import google.generativeai as genai

# Import shared configuration — categories, model name, and defaults all live here
from config import (
    ARXIV_CATEGORIES,
    EMBEDDING_MODEL,
    DEFAULT_MAX_RESULTS,
    DEFAULT_DELAY_SECONDS,
    DEFAULT_NUM_RETRIES,
    DEFAULT_OUTPUT_FILE,
)

# ── Load environment variables ─────────────────────────────────────────────────
# load_dotenv() reads your .env file and loads GEMINI_API_KEY into the
# environment. Must be called before os.getenv() or the key won't be found.
load_dotenv()

# ── Configure Gemini ───────────────────────────────────────────────────────────
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found. "
        "Make sure your .env file exists and contains GEMINI_API_KEY=your-key"
    )

genai.configure(api_key=api_key)

# ── Choose a category ──────────────────────────────────────────────────────────
# We pick by human-readable label and look up the arXiv code from config.
# Later the FastAPI backend will pass whichever category the user picked
# in the frontend dropdown — same pattern, just coming from the API instead.
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

client = arxiv.Client(
    page_size=100,
    delay_seconds=DEFAULT_DELAY_SECONDS,
    num_retries=DEFAULT_NUM_RETRIES,
)

papers = list(client.results(search))
print(f"Fetched {len(papers)} papers\n")

# ── Generate embeddings and collect results ────────────────────────────────────
# For each paper, we embed title + abstract together.
# Combining them gives richer context than embedding just the abstract.
# task_type="RETRIEVAL_DOCUMENT" tells Gemini we're embedding documents
# to be searched later — it optimises the embedding for this use case.
# When we embed a user's question in Session 4, we'll use
# task_type="RETRIEVAL_QUERY" instead.
print("Generating embeddings...")
print("-" * 60)

output = []

for i, paper in enumerate(papers, start=1):

    # Combine title and abstract for richer embedding
    text_to_embed = f"Title: {paper.title}\n\nAbstract: {paper.summary}"

    # Call Gemini embedding API
    response = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text_to_embed,
        task_type="RETRIEVAL_DOCUMENT",
    )

    # The embedding is a list of floats — response["embedding"] accesses it
    embedding = response["embedding"]

    # Print progress — we don't print all 768 numbers, just a summary
    print(f"\n{i}. {paper.title[:80]}...")
    print(f"   arXiv ID:         {paper.entry_id.split('/')[-1]}")
    print(f"   Embedding length: {len(embedding)} dimensions")
    print(f"   First 5 values:   {[round(v, 4) for v in embedding[:5]]}")

    # Collect everything for saving
    # We store both label and code so the frontend always has the
    # human-readable name alongside the arXiv code
    output.append({
        "arxiv_id": paper.entry_id.split("/")[-1],
        "title": paper.title,
        "authors": [a.name for a in paper.authors],
        "published": str(paper.published.date()),
        "category_label": SELECTED_CATEGORY_LABEL,
        "category_code": CATEGORY,
        "abstract": paper.summary,
        "embedding": embedding,
    })

# ── Save to JSON ───────────────────────────────────────────────────────────────
# Temporary — Session 3 replaces this with a proper database write.
with open(DEFAULT_OUTPUT_FILE, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n{'=' * 60}")
print(f"Saved {len(output)} papers with embeddings to {DEFAULT_OUTPUT_FILE}")