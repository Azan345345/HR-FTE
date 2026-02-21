"""
Digital FTE - ChromaDB Vector Store
"""

import chromadb

# Use local persistent ChromaDB (no Docker required)
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Collections
cv_collection = chroma_client.get_or_create_collection(
    name="user_cvs",
    metadata={"description": "Embedded CV sections for semantic matching"},
)

job_collection = chroma_client.get_or_create_collection(
    name="job_descriptions",
    metadata={"description": "Embedded job descriptions for matching"},
)
