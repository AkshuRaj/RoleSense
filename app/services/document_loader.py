import os
import pandas as pd
import re
from typing import List, Tuple, Dict

def chunk_markdown_document(content: str, file_name: str, max_chunk_size: int = 800) -> List[Tuple[str, Dict]]:
    """
    Intelligently chunk markdown documents while preserving context.
    
    Args:
        content: Full document content
        file_name: Name of the file for metadata
        max_chunk_size: Maximum characters per chunk
        
    Returns:
        List of (chunk_text, metadata) tuples
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chunk_size,
        chunk_overlap=150,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""]
    )
    
    # Very basic section tracking hack
    current_section = "Introduction"
    lines = content.split("\n")
    for line in lines:
        if line.startswith("## "):
            current_section = line.replace("## ", "").strip()
            break
            
    chunks = []
    split_docs = splitter.split_text(content)
    
    for doc in split_docs:
        metadata = {
            "section": current_section,
            "subsection": "",
            "file": file_name
        }
        chunks.append((doc, metadata))
        
    return chunks


def load_documents(base_path="resources/data"):
    """
    Load documents from the resources directory with intelligent chunking.
    """
    documents = []
    metadatas = []
    ids = []

    doc_id = 1

    for department in os.listdir(base_path):
        dept_path = os.path.join(base_path, department)
        
        if not os.path.isdir(dept_path):
            continue

        for file in os.listdir(dept_path):
            file_path = os.path.join(dept_path, file)
            
            if not os.path.isfile(file_path):
                continue

            # 🔥 HANDLE CSV FILES (HR DATA)
            if file.endswith(".csv"):
                try:
                    df = pd.read_csv(file_path)

                    for _, row in df.iterrows():
                        # Convert row → meaningful sentence with all fields
                        content = ", ".join(
                            [f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col])]
                        )

                        documents.append(content)
                        metadatas.append({
                            "department": department,
                            "file_type": "csv",
                            "file": file
                        })
                        ids.append(str(doc_id))
                        doc_id += 1
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

            # 🔥 HANDLE MD / TEXT FILES with intelligent chunking
            elif file.endswith(".md") or file.endswith(".txt"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                        # Clean up content
                        content = content.strip()
                        
                        # Use intelligent chunking for markdown
                        chunks_with_meta = chunk_markdown_document(content, file)
                        
                        for chunk_text, chunk_meta in chunks_with_meta:
                            if len(chunk_text.strip()) > 50:  # Only keep meaningful chunks
                                documents.append(chunk_text)
                                
                                # Combine metadata
                                meta = {
                                    "department": department,
                                    "file_type": "markdown",
                                    "file": file,
                                    "section": chunk_meta.get("section", ""),
                                    "subsection": chunk_meta.get("subsection", "")
                                }
                                metadatas.append(meta)
                                ids.append(str(doc_id))
                                doc_id += 1
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

    return documents, metadatas, ids


if __name__ == "__main__":
    docs, metas, ids = load_documents()

    print(f"Total chunks: {len(docs)}")
    print("\nSample document:")
    print(f"  Content: {docs[0][:200]}...")
    print(f"  Metadata: {metas[0]}")