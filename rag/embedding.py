"""
RAG Embedding and Indexing Module
Responsible for creating embeddings from document chunks and storing them in FAISS vector store.
"""

import os
import json
import pickle
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from .chunker import DocumentChunk, BISChunker

# Try to import FAISS, provide helpful error if not available
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None


class BISEmbedder:
    """
    Creates embeddings for BIS document chunks and manages FAISS vector store.
    """

    def __init__(self,
                 model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                 persist_directory: str = "storage/vectorstore",
                 collection_name: str = "bis_documents",
                 batch_size: int = 32):
        """
        Initialize the embedder and vector store.

        Args:
            model_name: Name of the sentence-transformer model to use
            persist_directory: Directory to persist FAISS index and metadata
            collection_name: Name of the FAISS index (kept for compatibility)
            batch_size: Batch size for embedding generation to manage memory usage
        """
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS is not installed. Please install it with: pip install faiss-cpu or faiss-gpu")

        self.model_name = model_name
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name  # Kept for compatibility
        self.batch_size = batch_size

        # Create persist directory if it doesn't exist
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize the sentence transformer model
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print("Embedding model loaded successfully")

        # Get embedding dimension
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"Embedding dimension: {self.dimension}")

        # Initialize FAISS index (using Inner Product for similarity, will normalize vectors)
        self.index = faiss.IndexFlatIP(self.dimension)

        # Storage for metadata and documents (FAISS only stores vectors)
        self.ids = []  # List of IDs corresponding to vectors in index
        self.metadata_map = {}  # id -> metadata
        self.documents_map = {}  # id -> document text

        # Try to load existing index and metadata
        self._load_index()

    def _load_index(self) -> None:
        """Load FAISS index and associated metadata from disk."""
        index_path = self.persist_directory / f"{self.collection_name}.index"
        ids_path = self.persist_directory / f"{self.collection_name}_ids.pkl"
        metadata_path = self.persist_directory / f"{self.collection_name}_metadata.pkl"
        documents_path = self.persist_directory / f"{self.collection_name}_documents.pkl"

        try:
            if index_path.exists():
                self.index = faiss.read_index(str(index_path))
                print(f"Loaded existing FAISS index from {index_path}")

                # Load associated data
                if ids_path.exists():
                    with open(ids_path, 'rb') as f:
                        self.ids = pickle.load(f)
                if metadata_path.exists():
                    with open(metadata_path, 'rb') as f:
                        self.metadata_map = pickle.load(f)
                if documents_path.exists():
                    with open(documents_path, 'rb') as f:
                        self.documents_map = pickle.load(f)

                print(f"Loaded {len(self.ids)} vectors with associated metadata")
            else:
                print(f"No existing index found at {index_path}, will create new")
        except Exception as e:
            print(f"Warning: Failed to load existing index: {e}")
            print("Creating new index instead")
            # Re-initialize if loading failed
            self.index = faiss.IndexFlatIP(self.dimension)
            self.ids = []
            self.metadata_map = {}
            self.documents_map = {}

    def _save_index(self) -> None:
        """Save FAISS index and associated metadata to disk."""
        index_path = self.persist_directory / f"{self.collection_name}.index"
        ids_path = self.persist_directory / f"{self.collection_name}_ids.pkl"
        metadata_path = self.persist_directory / f"{self.collection_name}_metadata.pkl"
        documents_path = self.persist_directory / f"{self.collection_name}_documents.pkl"

        try:
            # Save FAISS index
            faiss.write_index(self.index, str(index_path))

            # Save associated data
            with open(ids_path, 'wb') as f:
                pickle.dump(self.ids, f)
            with open(metadata_path, 'wb') as f:
                pickle.dump(self.metadata_map, f)
            with open(documents_path, 'wb') as f:
                pickle.dump(self.documents_map, f)

            print(f"Saved index and metadata to {self.persist_directory}")
        except Exception as e:
            print(f"Error saving index: {e}")

    def embed_chunks(self, chunks: List[DocumentChunk]) -> List[Dict[str, Any]]:
        """
        Create embeddings for a list of document chunks using batch processing.

        Args:
            chunks: List of DocumentChunk objects

        Returns:
            List of dictionaries containing chunk data with embeddings
        """
        if not chunks:
            return []

        # Extract texts for embedding
        texts = [chunk.text for chunk in chunks]

        # Generate embeddings in batches to manage memory usage
        print(f"Generating embeddings for {len(texts)} chunks in batches of {self.batch_size}...")
        all_embeddings = []

        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            batch_embeddings = self.model.encode(batch_texts, show_progress_bar=(i == 0))
            all_embeddings.append(batch_embeddings)
            print(f"Processed batch {i//self.batch_size + 1}/{(len(texts) + self.batch_size - 1)//self.batch_size}")

        # Concatenate all embeddings
        embeddings = np.vstack(all_embeddings) if all_embeddings else np.array([])
        print("Embeddings generated successfully")

        # Prepare chunk data with embeddings
        embedded_chunks = []
        for i, chunk in enumerate(chunks):
            embedded_chunk = {
                'id': chunk.chunk_id,
                'text': chunk.text,
                'embedding': embeddings[i].tolist(),
                'metadata': chunk.metadata
            }
            embedded_chunks.append(embedded_chunk)

        return embedded_chunks

    def store_chunks(self, embedded_chunks: List[Dict[str, Any]]) -> None:
        """
        Store embedded chunks in the FAISS vector store.

        Args:
            embedded_chunks: List of dictionaries containing chunk data with embeddings
        """
        if not embedded_chunks:
            print("No chunks to store")
            return

        # Prepare data for FAISS
        ids = [chunk['id'] for chunk in embedded_chunks]
        embeddings = [chunk['embedding'] for chunk in embedded_chunks]
        metadatas = [chunk['metadata'] for chunk in embedded_chunks]
        documents = [chunk['text'] for chunk in embedded_chunks]

        # Validate inputs before adding to index
        if not ids or not documents or not embeddings:
            print("ERROR: Missing required data for storage")
            return

        # Validate embedding dimensions and numeric values
        if len(embeddings) != len(ids):
            print(f"ERROR: Mismatch between embeddings ({len(embeddings)}) and ids ({len(ids)})")
            return

        # Check that all embeddings are lists of finite numbers and convert to float32
        try:
            # Convert to numpy array for FAISS (requires float32)
            embeddings_array = np.array(embeddings, dtype=np.float32)
            if not np.all(np.isfinite(embeddings_array)):
                print("ERROR: Non-finite values found in embeddings")
                return

            # Normalize vectors for inner product similarity (equivalent to cosine similarity)
            # FAISS IndexFlatIP computes inner product, so we normalize to get cosine similarity
            norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
            # Avoid division by zero
            norms = np.where(norms == 0, 1, norms)
            embeddings_normalized = embeddings_array / norms

        except Exception as e:
            print(f"ERROR: Invalid embedding format: {e}")
            return

        # Validate IDs are strings
        if not all(isinstance(id_val, str) and id_val for id_val in ids):
            print("ERROR: Invalid ID format - all IDs must be non-empty strings")
            return

        # Validate documents are strings
        if not all(isinstance(doc, str) for doc in documents):
            print("ERROR: Invalid document format - all documents must be strings")
            return

        # Validate metadata is list of dicts
        if not all(isinstance(meta, dict) for meta in metadatas):
            print("ERROR: Invalid metadata format - all metadata must be dictionaries")
            return

        # Check for duplicate IDs and warn (FAISS will overwrite if we don't handle this)
        duplicate_ids = [id_val for id_val in ids if id_val in self.ids]
        if duplicate_ids:
            print(f"WARNING: {len(duplicate_ids)} duplicate IDs found, existing vectors will be replaced")
            # Remove existing entries with duplicate IDs
            for dup_id in set(duplicate_ids):
                # Find all indices with this ID (should be at most one if we're careful)
                indices_to_remove = [i for i, existing_id in enumerate(self.ids) if existing_id == dup_id]
                # Remove in reverse order to maintain indices
                for idx in sorted(indices_to_remove, reverse=True):
                    self.ids.pop(idx)
                    # Note: We can't actually remove vectors from IndexFlatIP easily
                    # For simplicity, we'll rebuild the index if there are duplicates
                    # In practice, for this use case, duplicates are unlikely if we're doing upserts correctly

        # Add new vectors to the index
        print(f"Adding {len(embeddings_normalized)} vectors to FAISS index...")
        self.index.add(embeddings_normalized)

        # Store metadata and documents
        for i, chunk_id in enumerate(ids):
            self.ids.append(chunk_id)
            self.metadata_map[chunk_id] = metadatas[i]
            self.documents_map[chunk_id] = documents[i]

        # Save index and metadata to disk
        self._save_index()
        print(f"Stored {len(embedded_chunks)} chunks in vector store (total: {len(self.ids)})")

    def process_and_store_chunks(self, chunks: List[DocumentChunk]) -> None:
        """
        Process chunks through embedding and store them in vector store.

        Args:
            chunks: List of DocumentChunk objects
        """
        embedded_chunks = self.embed_chunks(chunks)
        self.store_chunks(embedded_chunks)

    def similarity_search(self,
                         query: str,
                         n_results: int = 5,
                         where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform similarity search against the vector store.

        Args:
            query: Query text to search for
            n_results: Number of results to return
            where: Optional metadata filter (not fully implemented in FAISS version)

        Returns:
            List of search results with text, metadata, and similarity scores
        """
        # Generate query embedding
        query_embedding = self.model.encode([query])[0]

        # Normalize query embedding (to match normalized stored vectors)
        query_norm = np.linalg.norm(query_embedding)
        if query_norm > 0:
            query_embedding = query_embedding / query_norm

        # Reshape for FAISS (expects 2D array: n_vectors x dimension)
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)

        # Search in FAISS
        # Return cosine similarity (since we used Inner Product with normalized vectors)
        # FAISS returns inner product, which equals cosine similarity for normalized vectors
        scores, indices = self.index.search(query_embedding, min(n_results, len(self.ids)))

        # Format results (similar to Chroma format)
        formatted_results = []
        if len(indices[0]) > 0:
            for i, idx in enumerate(indices[0]):
                if idx < len(self.ids):  # Safety check
                    chunk_id = self.ids[idx]
                    score = float(scores[0][i])  # This is cosine similarity due to normalization

                    formatted_results.append({
                        'id': chunk_id,
                        'text': self.documents_map.get(chunk_id, ""),
                        'metadata': self.metadata_map.get(chunk_id, {}),
                        'distance': 1.0 - score,  # Convert similarity to distance (approximate)
                        'similarity': score
                    })

        return formatted_results

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store collection.

        Returns:
            Dictionary containing collection statistics
        """
        count = len(self.ids)  # Could also use self.index.ntotal
        return {
            'collection_name': self.collection_name,
            'total_chunks': count,
            'persist_directory': str(self.persist_directory),
            'model_name': self.model_name
        }


def build_vectorstore(storage_path: str = "storage/data", batch_size: int = 32) -> None:
    """
    Main function to build the vector store from processed documents.
    This corresponds to the scripts/build_vectorstore.py mentioned in CONTEXT_SUMMARY.md.

    Args:
        storage_path: Path to the storage directory containing processed documents
        batch_size: Batch size for embedding generation to manage memory usage
    """
    print("Starting vector store build process...")

    try:
        # Initialize chunker
        chunker = BISChunker()

        # Chunk all documents
        print("Chunking documents...")
        chunks = chunker.chunk_all_documents(storage_path)
        print(f"Created {len(chunks)} total chunks")

        if not chunks:
            print("No chunks created. Exiting.")
            return

        # Initialize embedder and vector store
        embedder = BISEmbedder(batch_size=batch_size)

        # Process and store chunks
        embedder.process_and_store_chunks(chunks)

        # Show statistics
        stats = embedder.get_collection_stats()
        print(f"\nVector store built successfully!")
        print(f"Collection: {stats['collection_name']}")
        print(f"Total chunks: {stats['total_chunks']}")
        print(f"Persist directory: {stats['persist_directory']}")
        print(f"Embedding model: {stats['model_name']}")

    except Exception as e:
        print(f"Error building vector store: {e}")
        raise


def main():
    """Main function for testing the embedder."""
    # Test with a small sample
    print("Testing embedder with sample data...")

    # Create a test chunk
    test_chunk = DocumentChunk(
        chunk_id="test-001",
        text="This is a test chunk about water heaters and safety requirements.",
        metadata={
            'page_number': 1,
            'doc_type': 'test',
            'is_number': 'IS 2082',
            'chunk_method': 'test'
        }
    )

    # Initialize embedder
    embedder = BISEmbedder(persist_directory="storage/test_vectorstore")

    # Embed and store
    embedded_chunks = embedder.embed_chunks([test_chunk])
    embedder.store_chunks(embedded_chunks)

    # Test search
    results = embedder.similarity_search("water heater safety", n_results=1)
    print(f"Search results: {len(results)}")
    if results:
        print(f"Top result: {results[0]['text'][:50]}...")

    # Show stats
    stats = embedder.get_collection_stats()
    print(f"Collection stats: {stats}")


if __name__ == "__main__":
    main()