"""
app/embeddings.py

Gemini-related helpers. One Gemini client lives here, and any code
that needs to embed text or generate answers calls these functions.
"""

import os
from google import genai
from config import EMBEDDING_MODEL

# -- Gemini client setup --
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

gemini_client = genai.Client(api_key=api_key)

# -- Embedding helper function --
def embed_query(text: str) -> list[float]:
    """
    Convert a piece of text into an embedding vector.
    Used for both documents (during ingestion) and queries (during search).
    """
    response = gemini_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )
    return list(response.embeddings[0].values)

# -- Answer generation helper function (for future use) --
def generate_answer_stream(prompt: str):
    """
    Generate an answer from Gemini and yield it chunk by chunk.
    A generator — caller iterates to get pieces of the response as they arrive.
    """
    stream = gemini_client.models.generate_content_stream(
        model="models/gemini-2.5-flash",
        contents=prompt,
    )
    for chunk in stream:
        if chunk.text:
            yield chunk.text