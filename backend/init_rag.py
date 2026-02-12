"""
Initialize RAG database with templates and examples.
Run this once to populate the vector database.

Usage: python init_rag.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import rag_service


def main():
    print("=" * 60)
    print("BharatBuild RAG Database Initialization")
    print("=" * 60)

    # Check if dependencies are available
    if not rag_service.is_available():
        print("\n[ERROR] RAG dependencies not installed!")
        print("Install with:")
        print("  pip install chromadb sentence-transformers")
        return 1

    print("\n[1] Loading documents from rag_data directory...")
    rag_service.load_from_directory()

    print("\n[2] Getting database statistics...")
    stats = rag_service.get_stats()

    print("\nRAG Database Status:")
    print(f"  - Path: {stats['db_path']}")
    print(f"  - Initialized: {stats['initialized']}")
    print("\nCollections:")

    total_docs = 0
    for ctype, info in stats['collections'].items():
        if 'count' in info:
            count = info['count']
            total_docs += count
            print(f"  - {ctype}: {count} documents")
        elif 'error' in info:
            print(f"  - {ctype}: ERROR - {info['error']}")

    print(f"\nTotal documents: {total_docs}")

    # Test retrieval
    print("\n[3] Testing retrieval...")

    test_queries = [
        ("Create a login form with validation", "react"),
        ("FastAPI CRUD endpoint for users", "fastapi"),
        ("Cannot read property map of undefined", None),
    ]

    for query, framework in test_queries:
        print(f"\nQuery: '{query[:50]}...'")
        if framework:
            print(f"Framework: {framework}")

        context = rag_service.retrieve_for_code_generation(
            prompt=query,
            framework=framework,
            n_results=2
        )

        if context:
            print(f"  Retrieved context: {len(context)} chars")
            # Show first 200 chars of context
            preview = context[:200].replace('\n', ' ')
            print(f"  Preview: {preview}...")
        else:
            print("  No relevant context found")

    print("\n" + "=" * 60)
    print("RAG initialization complete!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
