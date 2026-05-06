# 01-arxiv-rag

A personal research tool for exploring physics and AI/ML papers from arXiv.

## What it does
- Ingests papers from arXiv (soft matter, biophysics, statistical physics, complex systems, AI/ML, econophysics)
- Stores papers and their embeddings in a vector database (PostgreSQL + pgvector)
- Answers questions about the literature using RAG (retrieval-augmented generation)
- Generates trend reports and mini-reviews for specific fields

## Stack
- **Backend:** FastAPI
- **Frontend:** Streamlit (React later)
- **Database:** PostgreSQL + pgvector
- **AI:** Google Gemini (embeddings + chat)
- **Infrastructure:** Docker, GCP Cloud Run, Cloud SQL
- **CI/CD:** GitHub Actions

## Project status
🚧 In progress — built as a learning project.

## Run locally
\```bash
git clone https://github.com/yourname/01-arxiv-rag.git
cd 01-arxiv-rag
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python fetch_papers.py
\```