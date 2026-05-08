"""
app/main.py

The FastAPI application. Defines the HTTP endpoints exposed by the backend.

Run locally with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from fastapi.responses import StreamingResponse
from app.embeddings import embed_query, generate_answer_stream
from app.database import search_papers


# --Create the FastAPI app instance --
app = FastAPI(
    title="arXiv RAG API",
    description="Semantic search and Q&A over arXiv papers",
    version="0.1.0",
)

# -- Request / Response models --
# Pydantic models define the expected shape of input and output.
# Field(...) adds validation rules and example values.

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results")


class PaperResult(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str]
    published: str
    category_label: str
    abstract: str
    similarity: float


class SearchResponse(BaseModel):
    query: str
    results: list[PaperResult]

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)

# -- API endpoints --

# -- health check endpoint --
@app.get("/health")
def health_check():
    """
    Simple liveness endpoint.
    Cloud platforms ping this to know the service is running.
    """
    return {"status": "ok"}

# -- search endpoint --
@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    """
    Semantic search over the papers database.
    Returns the top-K most relevant papers for the query.
    """
    try:
        query_vector = embed_query(request.query)
        papers = search_papers(query_vector, top_k=request.top_k)
        return SearchResponse(query=request.query, results=papers)
    except Exception as e:
        # Wrap any failure in an HTTP error so the client sees a clean
        # response.
        raise HTTPException(status_code=500, detail=str(e))

# -- chat endpoint --
def build_rag_prompt(query: str, papers: list[dict]) -> str:
    """
    Construct the prompt sent to Gemini.
    Includes retrieved papers as context, then asks the model
    to answer using only that context and to cite arXiv IDs.
    """
    context_blocks = []
    for i, paper in enumerate(papers, start=1):
        context_blocks.append(
            f"[Paper {i}] arXiv:{paper['arxiv_id']}\n"
            f"Title: {paper['title']}\n"
            f"Abstract: {paper['abstract']}\n"
        )

    context = "\n---\n".join(context_blocks)

    prompt = f"""You are a research assistant answering questions about academic papers.

Use ONLY the papers below to answer the question. If the papers do not contain
enough information to answer, say so honestly. Cite papers by their arXiv ID
in square brackets like [arXiv:1234.56789].

PAPERS:
{context}

QUESTION:
{query}

ANSWER:"""

    return prompt


@app.post("/chat")
def chat(request: ChatRequest):
    """
    Retrieval-augmented chat.
    1. Find papers most relevant to the question
    2. Build a prompt with those papers as context
    3. Stream Gemini's answer back token by token
    """
    try:
        query_vector = embed_query(request.query)
        papers = search_papers(query_vector, top_k=request.top_k)

        if not papers:
            raise HTTPException(
                status_code=404,
                detail="No papers found in the database",
            )

        prompt = build_rag_prompt(request.query, papers)
        return StreamingResponse(
            generate_answer_stream(prompt),
            media_type="text/plain",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    