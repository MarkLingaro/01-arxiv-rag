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
    "Complex Systems": "physics.complex-ph",
    "Fluid Dynamics": "physics.flu-dyn",
    "Biophysics": "biology.bio-ph"
}

# -- Embedding settings --
EMBEDDING_MODEL = "models/gemini-embedding-2"  # Gemini embedding model
EMBEDDING_DIMENSION = 1024  # Gemini embedding dimension

# -- Ingestion settings --
DEFAULT_MAX_RESULTS = 20  # Default number of papers to fetch per category
DEFAULT_DELAY_SECONDS = 3.0
DEFAULT_NUM_RETRIES = 3

# -- Output settings --
DEFAULT_OUTPUT_FILE = "papers_with_embeddings.json"  # Output file for ingested papers