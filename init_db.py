"""
init_db.py

Creates DB schema:
- enable pgvector extension
- create papers table with vector column

Can be run multiple times without error (idempotent).
uses IF NOT EXISTS everywhere. 

Run with: python init_db.py
"""

import psycopg
from config import DB_URL, EMBEDDING_DIMENSIONS

#SQL to create all that is needed
SCHEMA_SQL = f"""
-- Enable pgvector extension if it isn't already
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the papers table
CREATE TABLE IF NOT EXISTS papers (
    id              SERIAL PRIMARY KEY,
    arxiv_id        TEXT UNIQUE NOT NULL,
    title           TEXT NOT NULL,
    authors         TEXT[],                    -- array of author names
    published       DATE,
    category_label  TEXT,
    category_code   TEXT,
    abstract        TEXT,
    embedding       VECTOR({EMBEDDING_DIMENSIONS}),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Index on category for fast filtering
CREATE INDEX IF NOT EXISTS papers_category_idx ON papers (category_code);
"""

print("Connecting to database...")
print(f"Host: {DB_URL.split('@')[1]}")

# open a connection
with psycopg.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        print("Running schema setup...")
        cur.execute(SCHEMA_SQL)
        conn.commit()

print("Database initialised successfully.")
print("Table 'papers' is ready.")