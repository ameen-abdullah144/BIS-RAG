"""
Test script to build vector store with just a few chunks
"""
import sys
import os
from pathlib import Path

# Add the project root to the path so we can import our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag.embedding import build_vectorstore


def main():
    """Main function to test vector store build with limited chunks."""
    print("Testing BIS RAG Vector Store Build (limited chunks)")
    print("=" * 50)

    try:
        # We'll modify the build_vectorstore function to limit chunks for testing
        # But for now, let's just use a very small batch size and see if we can isolate the issue

        # First, let's try to chunk the documents and see how many we get
        from rag.chunker import BISChunker
        chunker = BISChunker()

        print("Chunking documents...")
        chunks = chunker.chunk_all_documents(storage_path="storage/data")
        print(f"Created {len(chunks)} total chunks")

        if len(chunks) > 0:
            print(f"First chunk text preview: {chunks[0].text[:100]}...")
            print(f"First chunk metadata: {chunks[0].metadata}")

        # Now try to process just the first 5 chunks
        test_chunks = chunks[:5] if len(chunks) >= 5 else chunks
        print(f"Testing with {len(test_chunks)} chunks")

        from rag.embedding import BISEmbedder
        embedder = BISEmbedder(persist_directory="storage/test_vectorstore", batch_size=4)

        print("Processing and storing test chunks...")
        embedder.process_and_store_chunks(test_chunks)

        # Show statistics
        stats = embedder.get_collection_stats()
        print(f"\nTest vector store built successfully!")
        print(f"Collection: {stats['collection_name']}")
        print(f"Total chunks: {stats['total_chunks']}")
        print(f"Persist directory: {stats['persist_directory']}")
        print(f"Embedding model: {stats['model_name']}")

    except Exception as e:
        print(f"Error building vector store: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()