"""
Simple test to check if the embedding model works
"""
from sentence_transformers import SentenceTransformer

print("Loading model...")
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
print("Model loaded successfully")

print("Encoding test sentence...")
embedding = model.encode(["This is a test sentence."])
print(f"Embedding shape: {embedding.shape}")
print("Test completed successfully")