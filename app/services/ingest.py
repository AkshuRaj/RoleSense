from app.services.document_loader import load_documents
from app.services.embedding_service import get_embedding
from app.services.vector_store import add_documents


def ingest_data():
    print("Loading documents...")
    docs, metas, ids = load_documents()

    print(f"Total chunks: {len(docs)}")

    print("Creating embeddings...")
    embeddings = [get_embedding(doc).tolist() for doc in docs]

    print("Storing in Chroma...")
    add_documents(docs, embeddings, metas, ids)

    print("✅ Data ingestion complete!")


if __name__ == "__main__":
    ingest_data()