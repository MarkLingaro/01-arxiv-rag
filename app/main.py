"""
app/main.py

The FastAPI application. Defines the HTTP endpoints exposed by the backend.

Run locally with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from fastapi.responses import StreamingResponse
from app.embeddings import embed_query, generate_answer_stream
from app.database import search_papers
from config import ARXIV_CATEGORIES

# -- Logging --

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

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
    return {"status": "ok", "version": "1.1.0"}

# -- search endpoint --
@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    try:
        logger.info(f"Search request: '{request.query[:60]}...' top_k={request.top_k}")
        query_vector = embed_query(request.query)
        papers = search_papers(query_vector, top_k=request.top_k)
        return SearchResponse(query=request.query, results=papers)
    except Exception as e:
        logger.exception("Error in /search endpoint")
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

    Errors that happen BEFORE streaming starts (auth, embedding failure,
    no papers) raise proper HTTP errors with status codes.

    Errors that happen DURING streaming get embedded as [ERROR] messages
    inside the stream — see generate_answer_stream() in embeddings.py.
    """
    try:
        # These run before streaming starts — real HTTP errors are possible
        logger.info(f"Chat request received: '{request.query[:60]}...'")

        query_vector = embed_query(request.query)
        papers = search_papers(query_vector, top_k=request.top_k)

        if not papers:
            logger.warning("No papers found in database for chat request")
            raise HTTPException(
                status_code=404,
                detail=(
                    "No papers found in the database. "
                    "Run embed_papers.py and load_to_db.py first to ingest papers."
                ),
            )

        prompt = build_rag_prompt(request.query, papers)
        logger.info(f"Streaming response for {len(papers)} retrieved papers")

        return StreamingResponse(
            generate_answer_stream(prompt),
            media_type="text/plain",
        )

    except HTTPException:
        # Re-raise — don't wrap in another 500
        raise
    except Exception as e:
        logger.exception("Unhandled error in /chat endpoint")
        raise HTTPException(status_code=500, detail=str(e))
    
# -- Fetch category labels (for frontend dropdown) --
@app.get("/categories")
def list_categories():
    """
    Return the list of arXiv categories and their labels.
    The frontend calls this to populate the category filter dropdown.
    """
    return {"categories": list(ARXIV_CATEGORIES.keys())}