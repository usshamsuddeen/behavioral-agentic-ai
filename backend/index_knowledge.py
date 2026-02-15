"""
Index sample knowledge base documents into vector store.
"""
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

print("\n" + "=" * 60)
print("    KNOWLEDGE BASE INDEXING")
print("=" * 60)

from app.ai.vector_store import get_vector_store

vector_store = get_vector_store()

# Load FAQs
print("\n[1] Loading FAQ documents...")
faq_path = Path("data/sample_faqs.json")
if faq_path.exists():
    with open(faq_path, 'r', encoding='utf-8') as f:
        faqs = json.load(f)
    
    documents = []
    metadatas = []
    for faq in faqs:
        # Combine title and answer for better retrieval
        doc = f"Q: {faq['title']}\nA: {faq['answer']}"
        documents.append(doc)
        metadatas.append({
            "title": faq["title"],
            "category": faq.get("category", "general"),
            "type": faq.get("type", "faq"),
            "source": "faq"
        })
    
    ids = vector_store.add_documents(
        documents=documents,
        metadatas=metadatas,
        collection_name="knowledge_base"
    )
    print(f"[OK] Indexed {len(ids)} FAQ documents")
else:
    print("[WARN] FAQ file not found")

# Load Policies
print("\n[2] Loading Policy documents...")
policy_path = Path("data/sample_policies.json")
if policy_path.exists():
    with open(policy_path, 'r', encoding='utf-8') as f:
        policies = json.load(f)
    
    documents = []
    metadatas = []
    for policy in policies:
        doc = f"{policy['title']}\n{policy['content']}"
        documents.append(doc)
        metadatas.append({
            "title": policy["title"],
            "section": policy.get("section", "general"),
            "type": policy.get("type", "policy"),
            "source": "policy"
        })
    
    ids = vector_store.add_documents(
        documents=documents,
        metadatas=metadatas,
        collection_name="knowledge_base"
    )
    print(f"[OK] Indexed {len(ids)} Policy documents")
else:
    print("[WARN] Policy file not found")

# Test search
print("\n[3] Testing retrieval...")
test_queries = [
    "How do I return a product?",
    "What are the shipping options?",
    "Can I get a refund?"
]

for query in test_queries:
    results = vector_store.search(
        query=query,
        collection_name="knowledge_base",
        n_results=2
    )
    print(f"\nQuery: '{query}'")
    for r in results:
        title = r.get("metadata", {}).get("title", "N/A")
        sim = r.get("similarity", 0)
        print(f"  - {title} (sim: {sim:.3f})")

# Stats
stats = vector_store.get_collection_stats("knowledge_base")
print(f"\n[4] Collection stats: {stats}")

print("\n" + "=" * 60)
print("    INDEXING COMPLETE")
print("=" * 60 + "\n")
