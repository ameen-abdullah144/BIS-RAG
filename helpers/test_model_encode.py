"""
Test model.encode with actual chunk text
"""
from rag.chunker import BISChunker

def main():
    """Test model encoding with actual chunk text."""
    print("Testing model encoding with actual chunk text")
    print("=" * 50)

    try:
        # Get the chunks
        chunker = BISChunker()
        print("Chunking documents...")
        chunks = chunker.chunk_all_documents(storage_path="storage/data")
        print(f"Created {len(chunks)} total chunks")

        if len(chunks) == 0:
            print("No chunks found!")
            return

        # Get the text from the first chunk
        test_text = chunks[0].text
        print(f"Text length: {len(test_text)} characters")
        print(f"Text preview: {test_text[:200]}...")

        # Try to encode it
        from sentence_transformers import SentenceTransformer
        print("Loading embedding model...")
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        print("Model loaded successfully")

        print("Encoding text...")
        embedding = model.encode([test_text])  # Note: encode expects a list
        print(f"Encoding successful! Shape: {embedding.shape}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()