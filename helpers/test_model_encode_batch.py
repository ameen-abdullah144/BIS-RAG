"""
Test model.encode with multiple chunk texts
"""
from rag.chunker import BISChunker

def main():
    """Test model encoding with multiple chunk texts."""
    print("Testing model encoding with multiple chunk texts")
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

        # Get the texts from the first 5 chunks
        test_texts = [chunk.text for chunk in chunks[:5]]
        print(f"Testing with {len(test_texts)} texts")
        for i, text in enumerate(test_texts):
            print(f"Text {i+1} length: {len(text)} characters")

        # Try to encode them
        from sentence_transformers import SentenceTransformer
        print("Loading embedding model...")
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        print("Model loaded successfully")

        print("Encoding texts...")
        embeddings = model.encode(test_texts)  # Note: encode expects a list
        print(f"Encoding successful! Shape: {embeddings.shape}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()