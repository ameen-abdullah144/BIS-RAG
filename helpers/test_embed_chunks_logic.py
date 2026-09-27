"""
Test the exact logic used in embed_chunks method
"""
from rag.chunker import BISChunker
from sentence_transformers import SentenceTransformer

def main():
    """Test the exact embedding logic."""
    print("Testing embed_chunks logic")
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

        # Extract texts for embedding (exactly as in embed_chunks)
        texts = [chunk.text for chunk in chunks]
        print(f"Extracted {len(texts)} texts")

        # Use the same parameters as BISEmbedder
        batch_size = 16  # This is what we're using in the updated script
        model_name = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'

        print(f"Loading model: {model_name}")
        model = SentenceTransformer(model_name)
        print("Model loaded successfully")

        # Generate embeddings in batches (exactly as in embed_chunks)
        print(f"Generating embeddings for {len(texts)} chunks in batches of {batch_size}...")
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size} (size: {len(batch_texts)})")
            batch_embeddings = model.encode(batch_texts, show_progress_bar=(i == 0))
            all_embeddings.append(batch_embeddings)
            print(f"Batch {i//batch_size + 1} completed, shape: {batch_embeddings.shape}")

        # Concatenate all embeddings (exactly as in embed_chunks)
        import numpy as np
        if all_embeddings:
            embeddings = np.vstack(all_embeddings)
            print(f"All embeddings concatenated successfully! Shape: {embeddings.shape}")
        else:
            embeddings = np.array([])
            print("No embeddings to concatenate")

        print("Test completed successfully!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()