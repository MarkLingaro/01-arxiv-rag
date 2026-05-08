"""
config.py

Central configuration file for the arXiv RAG project.
Defines constants and settings used across the pipeline.
Add new categories here as needed.
"""

# -- arXiv categories to fetch from and codes --
# Keys -> human-readable category names
# Values -> arXiv category codes used in queries

# Full list of arXiv categories can be found here: https://arxiv.org/category_taxonomy
import os
from dotenv import load_dotenv

load_dotenv()


ARXIV_CATEGORIES = {
    "Soft Condensed Matter": "cond-mat.soft",
    "Statistical Mechanics": "cond-mat.stat-mech",
    "Materials Science": "cond-mat.mtrl-sci",
    "Biological Physics": "physics.bio-ph",
    "Machine Learning": "cs.LG",
    "Statistical Finance": "q.fin.ST",
    "Society and Social Sciences": "physics.soc-ph",
    "Data Analysis, Statistics and Probability": "physics.data-an",
    "Computational Physics": "physics.comp-ph",
    "Chemical Physics": "physics.chem-ph",
    "Fluid Dynamics": "physics.flu-dyn"
}

# -- Embedding settings --
EMBEDDING_MODEL = "models/gemini-embedding-2"  # Gemini embedding model
EMBEDDING_DIMENSIONS = 3072  # Gemini embedding dimension

# -- Ingestion settings --
DEFAULT_MAX_RESULTS = 100  # Default number of papers to fetch per category
DEFAULT_DELAY_SECONDS = 3.0
DEFAULT_NUM_RETRIES = 3

# -- Output settings --
DEFAULT_OUTPUT_FILE = "papers_with_embeddings.json"  # Output file for ingested papers

## -- DB settings --
# Values are read from .env file
# Can be used with GCP Secret Manager

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "arxiv")
DB_USER = os.getenv("DB_USER", "arxiv")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Sanity check — fail loudly if password is missing
if not DB_PASSWORD:
    raise ValueError(
        "DB_PASSWORD not found in .env. "
        "Make sure your .env file contains all DB_ variables."
    )

# Convenient connection string format used by Postgres clients
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
