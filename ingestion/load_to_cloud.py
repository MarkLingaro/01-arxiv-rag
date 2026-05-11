"""
ingestion/load_to_cloud.py

Phase 2 of the ingestion pipeline.

Downloads staging files from GCS, loads them into Cloud SQL,
and archives the processed files.

Requires:
  - Cloud SQL instance to be RUNNABLE
  - Cloud SQL Auth Proxy running on localhost:5432
    OR DB_HOST pointing at a reachable Postgres

Run with:
    python ingestion/load_to_cloud.py

Or skip the GCS download (use local staging files only):
    python ingestion/load_to_cloud.py --no-download
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Make project root importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg
from dotenv import load_dotenv

from config import DB_URL

load_dotenv()

# -- CLI --
parser = argparse.ArgumentParser(description="Load staged papers into Cloud SQL")
parser.add_argument(
    "--no-download",
    action="store_true",
    help="Skip downloading from GCS; use existing files in ingestion/staging/",
)
args = parser.parse_args()

# -- Paths --
ingestion_dir = Path(__file__).resolve().parent
staging_dir = ingestion_dir / "staging"
archive_dir = ingestion_dir / "archive"
staging_dir.mkdir(parents=True, exist_ok=True)
archive_dir.mkdir(parents=True, exist_ok=True)

# -- Load from GCS --
if not args.no_download:
    project_id = os.popen("gcloud config get-value project").read().strip()
    print(f"DEBUG: project_id = '{project_id}'")  
    bucket_name = f"arxiv-rag-staging-{project_id}"
    print(f"DEBUG: bucket_name = '{bucket_name}'") 
    gcs_path = f"gs://{bucket_name}/staging/"
    print(f"DEBUG: gcs_path = '{gcs_path}'")

    print(f"Downloading staging files from {gcs_path}...")
    result = os.system(f"gcloud storage cp {gcs_path}*.json {staging_dir}/ 2>/dev/null")
    print(f"DEBUG: gcloud result = {result}")
    if result != 0:
        print("No files found in GCS or download failed. Will check local staging.")

# -- Find staging files --
staging_files = sorted(staging_dir.glob("papers_*.json"))

if not staging_files:
    print("No staging files to load. Exiting.")
    sys.exit(0)

print(f"\nFound {len(staging_files)} staging files:")
for f in staging_files:
    print(f"  {f.name}")

# -- SQL scripts --
INSERT_SQL = """
INSERT INTO papers (
    arxiv_id,
    title,
    authors,
    published,
    category_label,
    category_code,
    abstract,
    embedding
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (arxiv_id) DO NOTHING;
"""

# -- Load into Cloud SQL --
total_inserted = 0
total_skipped = 0
total_failed = 0

print(f"\nConnecting to database...")
try:
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            for staging_file in staging_files:
                print(f"\nLoading {staging_file.name}...")

                with open(staging_file) as f:
                    papers = json.load(f)

                inserted = 0
                skipped = 0
                failed = 0

                for paper in papers:
                    try:
                        cur.execute(INSERT_SQL, (
                            paper["arxiv_id"],
                            paper["title"],
                            paper["authors"],
                            paper["published"],
                            paper["category_label"],
                            paper["category_code"],
                            paper["abstract"],
                            paper["embedding"],
                        ))
                        if cur.rowcount == 1:
                            inserted += 1
                        else:
                            skipped += 1
                    except Exception as e:
                        print(f"  Failed to insert {paper.get('arxiv_id', '?')}: {e}")
                        failed += 1

                conn.commit()
                print(f"  Inserted: {inserted}, Skipped (already in DB): {skipped}, Failed: {failed}")

                # Archive the processed file
                archive_path = archive_dir / staging_file.name
                staging_file.rename(archive_path)
                print(f"  Archived to: {archive_path.relative_to(ingestion_dir.parent)}")

                total_inserted += inserted
                total_skipped += skipped
                total_failed += failed

except Exception as e:
    print(f"\nFatal database error: {e}")
    sys.exit(1)

# -- Summary --
print(f"\n{'=' * 70}")
print(f" Load complete")
print(f"{'=' * 70}")
print(f" Total inserted: {total_inserted}")
print(f" Total skipped:  {total_skipped}")
print(f" Total failed:   {total_failed}")
print(f"{'=' * 70}")


