import chromadb
from app.services.embedding_service import get_embedding

# Use PersistentClient for data persistence
client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_or_create_collection(name="company_data")


def add_documents(documents, embeddings, metadatas, ids):
    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )


def query_documents(query_embedding, n_results=3, role=None):
    """
    Query documents with role-based access control.
    
    RBAC Logic:
    - c_level role: Full access to ALL departments (no filtering)
    - Other roles: Access only their department + general
    
    Args:
        query_embedding: Vector representation of the query
        n_results: Number of results to return
        role: User role for RBAC filtering
    """
    # Query more documents than needed, then filter by role
    # (Chroma doesn't support where filters well, so we filter client-side)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results * 3  # Get 3x to compensate for filtering
    )
    
    # 🔐 RBAC FILTERING: Role-based access control for standard roles
    if role and role != "c_level":
        filtered_docs = []
        filtered_metas = []
        filtered_distances = []
        
        for doc, meta, distance in zip(
            results.get("documents", [[]])[0],
            results.get("metadatas", [[]])[0],
            results.get("distances", [[]])[0]
        ):
            # Standard role: can access their department + general only
            if meta["department"] == role or meta["department"] == "general":
                filtered_docs.append(doc)
                filtered_metas.append(meta)
                filtered_distances.append(distance)
        
        return {
            "documents": [filtered_docs[:n_results]],
            "metadatas": [filtered_metas[:n_results]],
            "distances": [filtered_distances[:n_results]]
        }
    
    # 👑 C-LEVEL BYPASS: Full access to all departments
    # C-level executives (CEO, CTO, CFO, etc.) need complete visibility across organization
    if role == "c_level":
        # Return results without filtering (all departments accessible)
        return {
            "documents": [results.get("documents", [[]])[0][:n_results]],
            "metadatas": [results.get("metadatas", [[]])[0][:n_results]],
            "distances": [results.get("distances", [[]])[0][:n_results]]
        }
    
    # No role provided: return raw results (backward compatibility)
    return results
