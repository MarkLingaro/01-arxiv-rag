"""
ingestion/ingest.py

Phase 1 of the ingestion pipeline.

Fetches recent papers from arXiv for every category in ARXIV_CATEGORIES,
generates embeddings with Gemini, and saves to a timestamped JSON file
in ingestion/staging/.

Does NOT require Cloud SQL — only Gemini API access.

Run with:
    python ingestion/ingest.py

Or for a single category:
    python ingestion/ingest.py --category "Soft Condensed Matter"

Or to also upload to GCS:
    python ingestion/ingest.py --upload
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

# Make project root importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import arxiv
from dotenv import load_dotenv
from google import genai

from config import ARXIV_CATEGORIES, EMBEDDING_MODEL, DEFAULT_MAX_RESULTS

load_dotenv()

# -- CLI --
parser = argparse.ArgumentParser(description="Ingest arXiv papers")
parser.add_argument(
    "--category",
    type=str,
    default=None,
    help="Only ingest this category (default: all categories)",
)
parser.add_argument(
    "--max-papers",
    type=int,
    default=DEFAULT_MAX_RESULTS,
    help=f"Papers per category (default: {DEFAULT_MAX_RESULTS})",
)
parser.add_argument(
    "--upload",
    action="store_true",
    help="Upload the staging file to GCS after creating it",
)
args = parser.parse_args()

# -- Categories to ingest --
if args.category:
    if args.category not in ARXIV_CATEGORIES:
        print(f"Unknown category: '{args.category}'")
        print(f"Available: {list(ARXIV_CATEGORIES.keys())}")
        sys.exit(1)
    categories_to_ingest = {args.category: ARXIV_CATEGORIES[args.category]}
else:
    categories_to_ingest = ARXIV_CATEGORIES

# -- Gemini client setup --
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    print("Error: GEMINI_API_KEY not set in environment")
    sys.exit(1)
client = genai.Client(api_key=gemini_api_key)

# -- Output file setup --
staging_dir = Path(__file__).resolve().parent / "staging"
staging_dir.mkdir(parents=True, exist_ok=True)

output_file = staging_dir / f"papers_{date.today().isoformat()}.json"
print(f"Output file: {output_file}")

# -- Fetch, embed, and collect papers --
all_papers = []

# Create one arxiv Client with built-in rate limiting
arxiv_client = arxiv.Client(
    page_size=100,
    delay_seconds=3.0,   # arXiv requires 3s between requests
    num_retries=3,
)

for label, code in categories_to_ingest.items():
    print(f"\n{'=' * 70}")
    print(f"Category: {label} ({code})")
    print(f"{'=' * 70}")

    search = arxiv.Search(
        query=f"cat:{code}",
        max_results=args.max_papers,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    try:
        papers = list(arxiv_client.results(search))
    except Exception as e:
        print(f"  Failed to fetch from arXiv: {e}")
        continue

    print(f"  Fetched {len(papers)} papers from arXiv")

    for i, paper in enumerate(papers, 1):
        try:
            text = f"Title: {paper.title}\n\nAbstract: {paper.summary}"
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
            )
            embedding = list(response.embeddings[0].values)

            all_papers.append({
                "arxiv_id": paper.entry_id.split("/")[-1],
                "title": paper.title,
                "authors": [a.name for a in paper.authors],
                "published": str(paper.published.date()),
                "category_label": label,
                "category_code": code,
                "abstract": paper.summary,
                "embedding": embedding,
            })

            short_title = paper.title[:60] + "..." if len(paper.title) > 60 else paper.title
            print(f"  [{i}/{len(papers)}] {short_title}")
        except Exception as e:
            print(f"  [{i}/{len(papers)}] FAILED: {e}")

# -- Save to staging file --
print(f"\nWriting {len(all_papers)} papers to {output_file}...")
with open(output_file, "w") as f:
    json.dump(all_papers, f)
print(f"Saved.")

# -- Upload to GCS if requested --
if args.upload:
    project_id = os.popen("gcloud config get-value project").read().strip()
    bucket_name = f"arxiv-rag-staging-{project_id}"
    gcs_path = f"gs://{bucket_name}/staging/{output_file.name}"

    print(f"\nUploading to {gcs_path}...")
    result = os.system(f"gcloud storage cp {output_file} {gcs_path}")
    if result == 0:
        print("Upload complete.")
    else:
        print("Upload failed. Check gcloud auth and bucket permissions.")
        sys.exit(1)

print("\nDone.")