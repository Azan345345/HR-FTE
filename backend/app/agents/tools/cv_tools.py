"""
Digital FTE - CV Tools (LangChain tools for the CV Parser agent)
Provides file reading, embedding generation, and ChromaDB storage.
"""

import structlog
from typing import List

from sentence_transformers import SentenceTransformer

from app.db.vector_store import cv_collection
from app.utils.file_handler import extract_text
from app.utils.text_processor import clean_text, chunk_text

logger = structlog.get_logger()

# Load embedding model (lazy singleton)
_embedding_model = None


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info("loading_embedding_model", model="all-MiniLM-L6-v2")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def read_cv_file(file_path: str, file_type: str) -> str:
    """Read and clean CV text from a file."""
    raw_text = extract_text(file_path, file_type)
    return clean_text(raw_text)


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of text chunks."""
    model = _get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()


def store_cv_embeddings(cv_id: str, user_id: str, text: str) -> str:
    """
    Chunk CV text, generate embeddings, and store in ChromaDB.
    Returns the embedding collection ID.
    """
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    if not chunks:
        logger.warning("no_chunks_to_embed", cv_id=cv_id)
        return ""

    embeddings = generate_embeddings(chunks)

    # IDs and metadata for ChromaDB
    ids = [f"{cv_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {"cv_id": cv_id, "user_id": user_id, "chunk_index": i}
        for i in range(len(chunks))
    ]

    cv_collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    logger.info("cv_embeddings_stored", cv_id=cv_id, num_chunks=len(chunks))
    return cv_id


def search_cv_by_query(query: str, n_results: int = 5, user_id: str = None) -> list:
    """Search CV embeddings by a query string."""
    query_embedding = generate_embeddings([query])[0]

    where_filter = {"user_id": user_id} if user_id else None

    results = cv_collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_filter,
    )

    return results
