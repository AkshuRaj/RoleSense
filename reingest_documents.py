"""
Reingest Script: Clear old ChromaDB and reingest all documents with improved chunking.

This script:
1. Backs up the old ChromaDB
2. Clears the collection
3. Reingests all documents with intelligent chunking
4. Validates the ingestion
"""

import os
import shutil
import chromadb
from datetime import datetime
from app.services.document_loader import load_documents
from app.services.embedding_service import get_embedding


def backup_chromadb():
    """Create a backup of the existing ChromaDB."""
    source = "./chroma_db"
    if os.path.exists(source):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"./chroma_db_backup_{timestamp}"
        shutil.copytree(source, backup_dir)
        print(f"✅ Backup created: {backup_dir}")
        return backup_dir
    return None


def clear_collection():
    """Delete and recreate the collection."""
    client = chromadb.PersistentClient(path="./chroma_db")
    
    try:
        client.delete_collection(name="company_data")
        print("✅ Old collection deleted")
    except Exception as e:
        print(f"⚠️  No existing collection to delete: {e}")
    
    # Create fresh collection
    collection = client.get_or_create_collection(name="company_data")
    print("✅ New collection created")
    return collection


def reingest_documents():
    """Load and reingest all documents."""
    print("\n" + "="*70)
    print("🔄 REINGESTING DOCUMENTS WITH IMPROVED CHUNKING")
    print("="*70 + "\n")
    
    # Step 1: Backup
    print("Step 1: Backing up existing data...")
    backup_dir = backup_chromadb()
    
    # Step 2: Clear collection
    print("\nStep 2: Clearing old collection...")
    collection = clear_collection()
    
    # Step 3: Load documents with improved chunking
    print("\nStep 3: Loading documents with intelligent chunking...")
    docs, metadatas, ids = load_documents()
    print(f"✅ Loaded {len(docs)} document chunks")
    
    if not docs:
        print("❌ No documents loaded! Check the resources/data directory.")
        return False
    
    # Step 4: Create embeddings
    print("\nStep 4: Creating embeddings...")
    try:
        embeddings = []
        for i, doc in enumerate(docs):
            if i % 10 == 0:
                print(f"  Processing chunk {i+1}/{len(docs)}...", end='\r')
            embedding = get_embedding(doc).tolist()
            embeddings.append(embedding)
        print(f"✅ Created {len(embeddings)} embeddings successfully")
    except Exception as e:
        print(f"❌ Error creating embeddings: {e}")
        return False
    
    # Step 5: Add to ChromaDB
    print("\nStep 5: Adding documents to ChromaDB...")
    try:
        collection.add(
            documents=docs,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        print(f"✅ Successfully added {len(docs)} chunks to ChromaDB")
    except Exception as e:
        print(f"❌ Error adding documents: {e}")
        return False
    
    # Step 6: Validation
    print("\nStep 6: Validating ingestion...")
    try:
        count = collection.count()
        print(f"✅ Collection count: {count} documents")
        
        # Show sample chunks by department
        print("\n📋 Sample chunks by department:")
        for meta in metadatas[:5]:
            dept = meta.get("department", "unknown")
            section = meta.get("section", "")
            file = meta.get("file", "")
            print(f"   • {dept}/{file} [{section}]")
        
        print(f"\n   ... and {len(metadatas) - 5} more chunks\n")
        
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False
    
    print("="*70)
    print("✅ REINGESTION COMPLETE!")
    print("="*70)
    print(f"\n📊 Summary:")
    print(f"   • Total chunks: {len(docs)}")
    print(f"   • Backup location: {backup_dir}")
    print(f"   • Ready for queries!\n")
    
    return True


def test_retrieval():
    """Test that retrieval works correctly."""
    print("🧪 Testing retrieval...\n")
    
    from app.services.embedding_service import get_embedding
    
    test_queries = [
        "What are the cloud providers used?",
        "Tell me about glossary terms",
        "What is the technology stack?",
        "What are HR policies?",
    ]
    
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(name="company_data")
    
    for query in test_queries:
        try:
            query_embedding = get_embedding(query).tolist()
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=2
            )
            
            docs = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            
            if docs:
                print(f"✅ Query: '{query}'")
                for i, (doc, meta) in enumerate(zip(docs, metadatas)):
                    section = meta.get("section", "")
                    dept = meta.get("department", "")
                    print(f"   Result {i+1}: {dept}/{section}")
                    print(f"      {doc[:100]}...")
            else:
                print(f"❌ Query: '{query}' - No results!")
            print()
        except Exception as e:
            print(f"❌ Error testing query: {e}\n")
    
    print("✅ Retrieval test complete!\n")


if __name__ == "__main__":
    # Run reingest
    success = reingest_documents()
    
    if success:
        # Test retrieval
        test_retrieval()
        print("\n🎉 All set! Your RAG chatbot is ready with improved chunking.\n")
    else:
        print("\n❌ Reingest failed. Check the errors above.\n")
