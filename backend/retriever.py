from pathlib import Path

import chromadb

from langchain_chroma import Chroma

from backend.ingestion import (
    load_repository,
    split_documents
)

from backend.embeddings import get_embedding_model


BASE_DIR = Path(__file__).resolve().parents[1]

VECTOR_DB_PATH = BASE_DIR / "data" / "chroma_db"


def get_collection_name(repo_id: str) -> str:
    """Generate a unique collection name for a repository."""
    # Sanitize repo_id to be valid collection name
    return f"repo_{repo_id}".replace('-', '_').replace('.', '_')


def index_repository(repo_path: str, repo_id: str):
    """
    Index a repository into ChromaDB with a unique collection.
    
    Args:
        repo_path: Path to the repository
        repo_id: Unique repository identifier
    
    Returns:
        Dict with success status and metadata
    """
    try:
        print(f"Loading repository from {repo_path}...")
        
        documents = load_repository(repo_path)
        print(f"Files loaded: {len(documents)}")

        if not documents:
            return {
                'success': False,
                'error': 'No documents found in repository'
            }

        print("Splitting documents...")
        chunks = split_documents(documents)
        print(f"Chunks generated: {len(chunks)}")

        print("Loading embedding model...")
        embeddings = get_embedding_model()

        collection_name = get_collection_name(repo_id)
        
        client = chromadb.PersistentClient(
            path=str(VECTOR_DB_PATH)
        )

        # Remove existing collection for this repo
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

        print("Creating vector database...")
        vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=collection_name,
            persist_directory=str(VECTOR_DB_PATH)
        )

        print("Repository successfully indexed!")

        return {
            'success': True,
            'collection_name': collection_name,
            'chunk_count': len(chunks),
            'document_count': len(documents)
        }

    except Exception as error:
        print(f"Indexing failed: {error}")
        return {
            'success': False,
            'error': str(error)
        }


def search_repository(query: str, repo_id: str, k: int = 2):
    """
    Search a specific repository's vector database.
    
    Args:
        query: Search query
        repo_id: Repository identifier
        k: Number of results to return
    """
    embeddings = get_embedding_model()
    collection_name = get_collection_name(repo_id)

    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(VECTOR_DB_PATH)
    )

    results = vector_store.similarity_search(
        query,
        k=k
    )

    return results


def get_collection_stats(repo_id: str) -> dict:
    """Get statistics for a repository's collection."""
    try:
        client = chromadb.PersistentClient(
            path=str(VECTOR_DB_PATH)
        )
        collection_name = get_collection_name(repo_id)
        collection = client.get_collection(collection_name)
        
        return {
            'exists': True,
            'count': collection.count()
        }
    except Exception:
        return {
            'exists': False,
            'count': 0
        }


if __name__ == "__main__":

    repo_path = BASE_DIR / "sample_repo"

    index_repository(str(repo_path))

    print("\nTesting semantic search...\n")

    results = search_repository(
        "How does the Corrective RAG workflow evaluate retrieved documents and decide whether to rewrite the query?"
    )

    for index, result in enumerate(results, start=1):

        print(f"\nResult {index}")
        print("Source:", result.metadata["source"])
        print("Content:")
        print(result.page_content[:500])
        print("-" * 60)