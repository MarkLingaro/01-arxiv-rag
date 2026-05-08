"""
app/embeddings.py

Gemini-related helpers. One Gemini client lives here, and any code
that needs to embed text or generate answers calls these functions.
"""

import os

from google import genai
from config import EMBEDDING_MODEL, CHAT_MODEL
import logging

logger = logging.getLogger(__name__)


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
    try:
        response = gemini_client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
        )
        return list(response.embeddings[0].values)

    except Exception as e:
        # Descriptive error so the calling endpoint
        # returns a meaningful HTTP error to the client.
        raise ValueError(
            f"Embedding failed for model '{EMBEDDING_MODEL}': {str(e)}"
        ) from e

# -- Answer generation helper function (for future use) --


def generate_answer_stream(prompt: str):
    """
    Generate an answer from Gemini and yield it chunk by chunk.

    If an error occurs mid-stream, we cannot change the HTTP status code
    (already sent as 200 OK). Instead we yield a clearly-formatted error
    message that the client can detect and display.
    """
    try:
        stream = gemini_client.models.generate_content_stream(
            model=CHAT_MODEL,
            contents=prompt,
        )
        for chunk in stream:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        # Log full details server-side
        logger.error(f"Streaming error from Gemini ({CHAT_MODEL}): {str(e)}")

        # Yield a clearly-marked error message into the stream.
        # The frontend will look for this prefix and display it as an error.
        yield f"\n\n[ERROR] Gemini API error: {str(e)}"