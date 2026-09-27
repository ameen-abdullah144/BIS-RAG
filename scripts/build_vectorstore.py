"""
Build Vector Store Script
Reads validated Phase 3 outputs, creates enriched text chunks,
computes multilingual embeddings, and persists to Chroma vector store.
This implements the scripts/build_vectorstore.py mentioned in CONTEXT_SUMMARY.md.
"""

import sys
import os
from pathlib import Path

# Add the project root to the path so we can import our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag.embedding import build_vectorstore


def main():
    """Main function to build the vector store."""
    print("Building BIS RAG Vector Store")
    print("=" * 50)

    try:
        # Build the vector store from processed documents
        # Using smaller batch size to manage memory usage
        build_vectorstore(storage_path="storage/data", batch_size=8)

        print("\n" + "=" * 50)
        print("Vector store build completed successfully!")
        print("The vector store is available at: storage/vectorstore/")

    except Exception as e:
        print(f"Error building vector store: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()