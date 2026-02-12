"""
RAG Service - Retrieval-Augmented Generation for BharatBuild AI

Uses ChromaDB (free, local) to store and retrieve:
- Code templates (React, FastAPI, etc.)
- Project examples
- Best practices
- Error solutions

This enhances Qwen/Claude responses with relevant context.
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import hashlib

from app.core.logging_config import logger
from app.core.config import settings

# Lazy imports for optional dependencies
chromadb = None
SentenceTransformer = None


def _import_chromadb():
    """Lazy import ChromaDB"""
    global chromadb
    if chromadb is None:
        try:
            import chromadb as _chromadb
            chromadb = _chromadb
        except ImportError:
            raise ImportError(
                "ChromaDB not installed. Install with: pip install chromadb"
            )
    return chromadb


def _import_sentence_transformer():
    """Lazy import SentenceTransformer for embeddings"""
    global SentenceTransformer
    if SentenceTransformer is None:
        try:
            from sentence_transformers import SentenceTransformer as _ST
            SentenceTransformer = _ST
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. Install with: pip install sentence-transformers"
            )
    return SentenceTransformer


@dataclass
class RetrievedDocument:
    """A document retrieved from the vector store"""
    content: str
    metadata: Dict[str, Any]
    score: float
    doc_type: str  # 'template', 'example', 'practice', 'solution'


class RAGService:
    """
    RAG Service for enhancing code generation with relevant context.

    Features:
    - Local vector database (ChromaDB) - no API costs
    - Multiple collections: templates, examples, practices, solutions
    - Automatic embedding with sentence-transformers
    - Easy to add new documents
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True
        self._client = None
        self._embedding_model = None
        self._collections = {}

        # RAG data directory
        self.data_dir = Path(__file__).parent / "rag_data"
        self.db_path = Path(settings.BASE_DIR) / "rag_db"

        # Collection names
        self.COLLECTIONS = {
            "templates": "code_templates",
            "examples": "project_examples",
            "practices": "best_practices",
            "solutions": "error_solutions"
        }

        logger.info(f"RAGService initialized (lazy loading), data_dir={self.data_dir}")

    def _get_client(self):
        """Get or create ChromaDB client"""
        if self._client is None:
            _import_chromadb()

            # Create persistent client
            self.db_path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self.db_path))
            logger.info(f"ChromaDB client initialized at {self.db_path}")

        return self._client

    def _get_embedding_model(self):
        """Get or create embedding model"""
        if self._embedding_model is None:
            _import_sentence_transformer()

            # Use a small, fast model for embeddings
            model_name = "all-MiniLM-L6-v2"  # 384 dimensions, very fast
            self._embedding_model = SentenceTransformer(model_name)
            logger.info(f"Embedding model loaded: {model_name}")

        return self._embedding_model

    def _get_collection(self, collection_type: str):
        """Get or create a collection"""
        if collection_type not in self._collections:
            client = self._get_client()
            collection_name = self.COLLECTIONS.get(collection_type, collection_type)

            self._collections[collection_type] = client.get_or_create_collection(
                name=collection_name,
                metadata={"description": f"BharatBuild {collection_type}"}
            )
            logger.info(f"Collection loaded: {collection_name}")

        return self._collections[collection_type]

    def _generate_id(self, content: str, metadata: Dict) -> str:
        """Generate unique ID for a document"""
        hash_input = f"{content[:100]}:{json.dumps(metadata, sort_keys=True)}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def add_document(
        self,
        content: str,
        collection_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a document to the vector store.

        Args:
            content: The document content (code, text, etc.)
            collection_type: 'templates', 'examples', 'practices', 'solutions'
            metadata: Additional metadata (framework, language, tags, etc.)

        Returns:
            Document ID
        """
        collection = self._get_collection(collection_type)
        model = self._get_embedding_model()

        metadata = metadata or {}
        metadata["type"] = collection_type

        doc_id = self._generate_id(content, metadata)

        # Generate embedding
        embedding = model.encode(content).tolist()

        # Add to collection
        collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata]
        )

        logger.info(f"Added document to {collection_type}: {doc_id[:8]}...")
        return doc_id

    def add_documents_batch(
        self,
        documents: List[Dict[str, Any]],
        collection_type: str
    ) -> List[str]:
        """
        Add multiple documents in batch.

        Args:
            documents: List of {"content": str, "metadata": dict}
            collection_type: Collection to add to

        Returns:
            List of document IDs
        """
        collection = self._get_collection(collection_type)
        model = self._get_embedding_model()

        ids = []
        embeddings = []
        contents = []
        metadatas = []

        for doc in documents:
            content = doc["content"]
            metadata = doc.get("metadata", {})
            metadata["type"] = collection_type

            doc_id = self._generate_id(content, metadata)
            ids.append(doc_id)
            embeddings.append(model.encode(content).tolist())
            contents.append(content)
            metadatas.append(metadata)

        # Batch add
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas
        )

        logger.info(f"Added {len(ids)} documents to {collection_type}")
        return ids

    def retrieve(
        self,
        query: str,
        collection_types: Optional[List[str]] = None,
        n_results: int = 3,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedDocument]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Search query (e.g., "React login form")
            collection_types: Which collections to search (default: all)
            n_results: Number of results per collection
            filter_metadata: Filter by metadata (e.g., {"framework": "react"})

        Returns:
            List of RetrievedDocument objects, sorted by relevance
        """
        model = self._get_embedding_model()
        query_embedding = model.encode(query).tolist()

        collection_types = collection_types or list(self.COLLECTIONS.keys())

        all_results = []

        for ctype in collection_types:
            try:
                collection = self._get_collection(ctype)

                # Build where clause if filter provided
                where = filter_metadata if filter_metadata else None

                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where
                )

                # Process results
                if results and results['documents'] and results['documents'][0]:
                    for i, doc in enumerate(results['documents'][0]):
                        distance = results['distances'][0][i] if results['distances'] else 0
                        score = 1 / (1 + distance)  # Convert distance to similarity score

                        metadata = results['metadatas'][0][i] if results['metadatas'] else {}

                        all_results.append(RetrievedDocument(
                            content=doc,
                            metadata=metadata,
                            score=score,
                            doc_type=ctype
                        ))

            except Exception as e:
                logger.warning(f"Error retrieving from {ctype}: {e}")

        # Sort by score (highest first)
        all_results.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"Retrieved {len(all_results)} documents for query: {query[:50]}...")
        return all_results

    def retrieve_for_code_generation(
        self,
        prompt: str,
        framework: Optional[str] = None,
        language: Optional[str] = None,
        n_results: int = 3
    ) -> str:
        """
        Retrieve context specifically for code generation.

        Args:
            prompt: User's code generation request
            framework: Target framework (react, fastapi, etc.)
            language: Programming language
            n_results: Number of results to include

        Returns:
            Formatted context string to append to prompt
        """
        # Build metadata filter
        filter_metadata = {}
        if framework:
            filter_metadata["framework"] = framework.lower()
        if language:
            filter_metadata["language"] = language.lower()

        # Retrieve from relevant collections
        results = self.retrieve(
            query=prompt,
            collection_types=["templates", "examples", "practices"],
            n_results=n_results,
            filter_metadata=filter_metadata if filter_metadata else None
        )

        if not results:
            return ""

        # Format context
        context_parts = []
        context_parts.append("\n<reference_context>")
        context_parts.append("Use the following references to improve your code generation:")

        for i, doc in enumerate(results[:n_results], 1):
            doc_type = doc.metadata.get("type", "reference")
            title = doc.metadata.get("title", f"Reference {i}")

            context_parts.append(f"\n### {doc_type.upper()}: {title}")
            context_parts.append(f"```")
            context_parts.append(doc.content[:2000])  # Limit size
            context_parts.append(f"```")

        context_parts.append("</reference_context>\n")

        return "\n".join(context_parts)

    def retrieve_error_solution(
        self,
        error_message: str,
        framework: Optional[str] = None,
        n_results: int = 2
    ) -> str:
        """
        Retrieve solutions for an error message.

        Args:
            error_message: The error to find solutions for
            framework: Framework context
            n_results: Number of solutions to return

        Returns:
            Formatted solutions string
        """
        filter_metadata = {"framework": framework.lower()} if framework else None

        results = self.retrieve(
            query=error_message,
            collection_types=["solutions"],
            n_results=n_results,
            filter_metadata=filter_metadata
        )

        if not results:
            return ""

        context_parts = []
        context_parts.append("\n<known_solutions>")
        context_parts.append("Similar errors and their solutions:")

        for doc in results:
            context_parts.append(f"\n{doc.content}")

        context_parts.append("</known_solutions>\n")

        return "\n".join(context_parts)

    def load_from_directory(self, directory: Optional[Path] = None):
        """
        Load documents from the rag_data directory.

        Expected structure:
        rag_data/
          templates/
            react/
              *.json
            fastapi/
              *.json
          examples/
            *.json
          practices/
            *.json
          solutions/
            *.json
        """
        directory = directory or self.data_dir

        if not directory.exists():
            logger.warning(f"RAG data directory not found: {directory}")
            return

        total_loaded = 0

        for collection_type in self.COLLECTIONS.keys():
            collection_dir = directory / collection_type

            if not collection_dir.exists():
                continue

            # Load all JSON files recursively
            for json_file in collection_dir.rglob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Handle both single doc and list of docs
                    if isinstance(data, list):
                        docs = data
                    else:
                        docs = [data]

                    for doc in docs:
                        if "content" in doc:
                            self.add_document(
                                content=doc["content"],
                                collection_type=collection_type,
                                metadata=doc.get("metadata", {})
                            )
                            total_loaded += 1

                except Exception as e:
                    logger.error(f"Error loading {json_file}: {e}")

        logger.info(f"Loaded {total_loaded} documents from {directory}")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG database"""
        stats = {
            "initialized": self._client is not None,
            "db_path": str(self.db_path),
            "collections": {}
        }

        if self._client:
            for ctype, cname in self.COLLECTIONS.items():
                try:
                    collection = self._get_collection(ctype)
                    stats["collections"][ctype] = {
                        "name": cname,
                        "count": collection.count()
                    }
                except Exception as e:
                    stats["collections"][ctype] = {"error": str(e)}

        return stats

    def clear_collection(self, collection_type: str):
        """Clear all documents from a collection"""
        client = self._get_client()
        collection_name = self.COLLECTIONS.get(collection_type, collection_type)

        try:
            client.delete_collection(collection_name)
            if collection_type in self._collections:
                del self._collections[collection_type]
            logger.info(f"Cleared collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error clearing collection {collection_name}: {e}")

    def is_available(self) -> bool:
        """Check if RAG service is available"""
        try:
            _import_chromadb()
            _import_sentence_transformer()
            return True
        except ImportError:
            return False


# Singleton instance
rag_service = RAGService()
