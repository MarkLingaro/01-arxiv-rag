import os
import requests
import streamlit as st
import sys
from pathlib import Path

# Add the project root to Python's import path 
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import ARXIV_CATEGORIES

# -- Configuration --
# Default to localhost:8000 for local development.
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

## -- Page setup --
st.set_page_config(
    page_title="arXiv RAG",
    page_icon="📚",
    layout="wide",
)

st.title("📚 arXiv RAG")
st.caption("Semantic search and Q&A over arXiv papers")

# -- Sidebar --
with st.sidebar:
    st.header("Settings")

    # Health check button — pings /health to confirm the backend is up
    if st.button("Check API status"):
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                st.success("API is healthy ✅")
            else:
                st.error(f"API returned status {response.status_code}")
        except Exception as e:
            st.error(f"Cannot reach API: {e}")

    st.divider()

    # Category filter — populated from config.py, single source of truth
    st.subheader("Filter")
    selected_category = st.selectbox(
        "Category",
        options=["All categories"] + list(ARXIV_CATEGORIES.keys()),
    )

    top_k = st.slider("Number of results", 1, 20, 5)

# -- Tabs for Search and Chat --
tab_search, tab_chat = st.tabs(["🔍 Search", "💬 Chat"])

with tab_search:
    st.subheader("Semantic search")
    st.caption("Find papers by meaning, not just keywords.")

    search_query = st.text_input(
        "What are you looking for?",
        placeholder="e.g. transformer architectures for time series data",
        key="search_query",
    )

    if st.button("Search", key="search_btn", type="primary"):
        if not search_query.strip():
            st.warning("Please enter a query.")
        else:
            with st.spinner("Searching..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/search",
                        json={"query": search_query, "top_k": top_k},
                        timeout=30,
                    )

                    if response.status_code != 200:
                        st.error(f"API error: {response.status_code} — {response.text}")
                    else:
                        data = response.json()
                        results = data["results"]

                        # Optional client-side category filter
                        if selected_category != "All categories":
                            results = [
                                r for r in results
                                if r["category_label"] == selected_category
                            ]

                        if not results:
                            st.info("No matching papers found.")
                        else:
                            st.success(f"Found {len(results)} matching papers.")

                            for i, paper in enumerate(results, start=1):
                                with st.expander(
                                    f"**{i}.** {paper['title']} "
                                    f"— similarity {paper['similarity']:.3f}"
                                ):
                                    st.markdown(
                                        f"**arXiv ID:** "
                                        f"[{paper['arxiv_id']}](https://arxiv.org/abs/{paper['arxiv_id']})"
                                    )
                                    st.markdown(
                                        f"**Authors:** {', '.join(paper['authors'][:5])}"
                                        f"{' et al.' if len(paper['authors']) > 5 else ''}"
                                    )
                                    st.markdown(f"**Published:** {paper['published']}")
                                    st.markdown(f"**Category:** {paper['category_label']}")
                                    st.markdown(f"**Abstract:** {paper['abstract']}")

                except requests.exceptions.Timeout:
                    st.error("Request timed out. The API took too long to respond.")
                except Exception as e:
                    st.error(f"Error: {e}")

with tab_chat:
    st.subheader("Ask a question")
    st.caption(
        "Get a synthesized answer with citations. "
        "The backend retrieves relevant papers, then asks Gemini to answer using them."
    )

    chat_query = st.text_area(
        "Your question",
        placeholder="e.g. What are recent approaches to phase transitions in active matter?",
        height=100,
        key="chat_query",
    )

    if st.button("Ask", key="chat_btn", type="primary"):
        if not chat_query.strip():
            st.warning("Please enter a question.")
        else:
            # Container to display the streaming answer.
            # st.empty() reserves a slot we can update in place.
            answer_container = st.empty()
            full_text = ""
            error_detected = False

            try:
                with requests.post(
                    f"{API_BASE_URL}/chat",
                    json={"query": chat_query, "top_k": top_k},
                    stream=True,                # don't read the whole response at once
                    timeout=60,
                ) as response:

                    if response.status_code != 200:
                        st.error(f"API error: {response.status_code} — {response.text}")
                    else:
                        # Read chunks as they arrive
                        for chunk in response.iter_content(
                            chunk_size=None,
                            decode_unicode=True,
                        ):
                            if not chunk:
                                continue

                            # Backend convention: errors mid-stream begin with [ERROR]
                            if "[ERROR]" in chunk:
                                error_detected = True

                            full_text += chunk
                            answer_container.markdown(full_text)

                        if error_detected:
                            st.warning(
                                "An error occurred during generation — "
                                "see the [ERROR] message above."
                            )

            except requests.exceptions.Timeout:
                st.error("Request timed out.")
            except Exception as e:
                st.error(f"Error: {e}")