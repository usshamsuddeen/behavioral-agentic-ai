"""
Test full RAG pipeline with knowledge base and LLM.
"""
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

print("\n" + "=" * 60)
print("    FULL RAG PIPELINE TEST")
print("=" * 60)

from app.ai.vector_store import get_vector_store
from app.ai.llm import get_llm_service

# Initialize services
vector_store = get_vector_store()
llm = get_llm_service()

print(f"\n[INFO] LLM Model: {llm.model}")
print(f"[INFO] Knowledge docs: {vector_store.get_collection_stats('knowledge_base').get('document_count', 0)}")

# Test query
test_question = "I bought a shirt 2 weeks ago and want to return it. What should I do?"

print(f"\n[QUERY] {test_question}")

# Step 1: Retrieve context
print("\n[1] Retrieving relevant documents...")
results = vector_store.search(
    query=test_question,
    collection_name="knowledge_base",
    n_results=3
)

context_docs = []
for r in results:
    title = r.get("metadata", {}).get("title", "N/A")
    text = r.get("text", "")
    sim = r.get("similarity", 0)
    print(f"  - {title} (sim: {sim:.3f})")
    context_docs.append(text)

# Step 2: Generate response
print("\n[2] Generating LLM response...")
print("    (Rate limit delay: 5 sec)")
time.sleep(5)  # Rate limit buffer

response = llm.generate_response(
    user_message=test_question,
    context_documents=context_docs,
    company_name="TestCo"
)

print(f"\n[3] Response Generated")
print(f"    Success: {response.success}")
print(f"    Model: {response.model}")
print(f"    Confidence: {response.confidence}")
print(f"    Tokens: {response.tokens_used}")

print(f"\n{'=' * 60}")
print("AI RESPONSE:")
print("=" * 60)
print(response.response)
print("=" * 60 + "\n")

# Summary
if response.success and response.confidence > 0.5:
    print("[OK] RAG Pipeline working - response generated with context")
elif response.success:
    print("[WARN] Response generated but confidence low (rate limited or fallback)")
else:
    print("[WARN] Response used fallback - LLM may be rate limited")
