"""
RAG Retriever Module
Responsible for retrieving relevant document chunks from the vector store
using hybrid search strategies with metadata filtering.
"""

from typing import List, Dict, Any, Optional
from .embedding import BISEmbedder
import logging

logger = logging.getLogger(__name__)


class BISRetriever:
    """
    Hybrid retriever for BIS document chunks with metadata filtering capabilities.
    """

    def __init__(self,
                 embedder: Optional[BISEmbedder] = None,
                 persist_directory: str = "storage/vectorstore",
                 collection_name: str = "bis_documents"):
        """
        Initialize the retriever.

        Args:
            embedder: BISEmbedder instance (if None, creates a new one)
            persist_directory: Directory where Chroma database is persisted
            collection_name: Name of the Chroma collection
        """
        if embedder is None:
            self.embedder = BISEmbedder(
                persist_directory=persist_directory,
                collection_name=collection_name
            )
        else:
            self.embedder = embedder

        # Default retrieval parameters
        self.default_n_results = 10
        self.rerank_top_k = 5

    def retrieve(self,
                query: str,
                n_results: int = 10,
                where: Optional[Dict[str, Any]] = None,
                rerank: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for a query using vector similarity search.

        Args:
            query: Query text to search for
            n_results: Number of results to return
            where: Optional metadata filter (e.g., {'is_number': 'IS 2082'})
            rerank: Whether to apply reranking (currently just returns top results)

        Returns:
            List of retrieved chunks with metadata and similarity scores
        """
        try:
            results = self.embedder.similarity_search(
                query=query,
                n_results=n_results,
                where=where
            )

            logger.info(f"Retrieved {len(results)} chunks for query: '{query[:50]}...'")

            # Apply reranking if requested (for now, just return top results)
            if rerank and len(results) > self.rerank_top_k:
                results = results[:self.rerank_top_k]

            return results

        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return []

    def retrieve_by_is_number(self,
                             query: str,
                             is_number: str,
                             n_results: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve chunks filtered by IS number.

        Args:
            query: Query text to search for
            is_number: IS number to filter by (e.g., 'IS 2082')
            n_results: Number of results to return

        Returns:
            List of retrieved chunks from the specified IS number
        """
        where_clause = {"is_number": is_number}
        return self.retrieve(
            query=query,
            n_results=n_results,
            where=where_clause
        )

    def retrieve_by_doc_type(self,
                            query: str,
                            doc_type: str,
                            n_results: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve chunks filtered by document type.

        Args:
            query: Query text to search for
            doc_type: Document type to filter by (e.g., 'product_manual')
            n_results: Number of results to return

        Returns:
            List of retrieved chunks of the specified document type
        """
        where_clause = {"doc_type": doc_type}
        return self.retrieve(
            query=query,
            n_results=n_results,
            where=where_clause
        )

    def retrieve_multiple_is_numbers(self,
                                    query: str,
                                    is_numbers: List[str],
                                    n_results: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve chunks filtered by multiple IS numbers.

        Args:
            query: Query text to search for
            is_numbers: List of IS numbers to filter by
            n_results: Number of results to return

        Returns:
            List of retrieved chunks from any of the specified IS numbers
        """
        # Chroma doesn't support $in operator directly, so we'll need to query each separately
        # For simplicity, we'll query without filter and then filter results
        # In a production system, we might want to implement a more efficient approach
        results = self.retrieve(query=query, n_results=n_results*2)  # Get extra results

        # Filter by IS numbers
        filtered_results = [
            result for result in results
            if result.get('metadata', {}).get('is_number') in is_numbers
        ]

        return filtered_results[:n_results]

    def hybrid_retrieve(self,
                       query: str,
                       n_results: int = 10,
                       where: Optional[Dict[str, Any]] = None,
                       keyword_weight: float = 0.3) -> List[Dict[str, Any]]:
        """
        Perform hybrid retrieval combining vector search with keyword matching.

        Args:
            query: Query text to search for
            n_results: Number of results to return
            where: Optional metadata filter
            keyword_weight: Weight for keyword scoring (0-1), remainder is vector weight

        Returns:
            List of retrieved chunks with combined scores
        """
        # Get vector search results
        vector_results = self.retrieve(
            query=query,
            n_results=n_results*2,  # Get more results for reranking
            where=where,
            rerank=False
        )

        if not vector_results:
            return []

        # Simple keyword scoring based on term frequency
        query_terms = set(query.lower().split())

        for result in vector_results:
            text = result.get('text', '').lower()
            text_terms = set(text.split())

            # Calculate Jaccard similarity for keyword matching
            if len(query_terms) > 0:
                intersection = len(query_terms.intersection(text_terms))
                union = len(query_terms.union(text_terms))
                keyword_score = intersection / union if union > 0 else 0
            else:
                keyword_score = 0

            # Combine vector similarity (already in result) with keyword score
            vector_score = result.get('similarity', 0)
            combined_score = (keyword_weight * keyword_score) + ((1 - keyword_weight) * vector_score)
            result['combined_score'] = combined_score
            result['keyword_score'] = keyword_score
            result['vector_score'] = vector_score

        # Rerank by combined score
        reranked_results = sorted(
            vector_results,
            key=lambda x: x.get('combined_score', 0),
            reverse=True
        )

        return reranked_results[:n_results]

    def get_retriever_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the retriever and underlying vector store.

        Returns:
            Dictionary containing retriever statistics
        """
        stats = self.embedder.get_collection_stats()
        stats.update({
            'retriever_type': 'hybrid_vector_keyword',
            'default_n_results': self.default_n_results,
            'rerank_top_k': self.rerank_top_k
        })
        return stats


def main():
    """Main function for testing the retriever."""
    print("Testing retriever...")

    # Initialize retriever
    retriever = BISRetriever(persist_directory="storage/test_vectorstore")

    # Test retrieval (will return empty if no data)
    results = retriever.retrieve("water heater safety requirements", n_results=5)
    print(f"Retrieved {len(results)} results")

    # Show stats
    stats = retriever.get_retriever_stats()
    print(f"Retriever stats: {stats}")


if __name__ == "__main__":
    main()