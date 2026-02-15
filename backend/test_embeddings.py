"""Quick test for embedding service."""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from app.ai.embeddings import get_embedding_service

print("Testing Embedding Service...")
e = get_embedding_service()
print(f"Provider: {e.get_model_info()}")

test_text = "Hello world, this is a test message"
embedding = e.embed_text(test_text)
print(f"Embedding dimension: {len(embedding)}")
print(f"First 5 values: {embedding[:5]}")

# Test similarity
sim = e.similarity("How do I return a product?", "What is your return policy?")
print(f"Similarity test: {sim:.3f}")

print("\n[SUCCESS] Embedding service is working!")
