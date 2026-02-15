"""
Quick test for OpenRouter LLM generation.
"""
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

print("\n[TEST] OpenRouter LLM Generation Test")
print("=" * 60)

from app.ai.llm import get_llm_service

llm = get_llm_service()
print(f"Model: {llm.model}")
print(f"API Configured: {llm.is_available()}")

# Wait for rate limit
print("\nWaiting 5 seconds for rate limit reset...")
time.sleep(5)

# Test generation
context = [
    "Our return policy allows returns within 30 days.",
    "Items must be in original packaging with receipt.",
    "Refunds are processed within 5-7 business days."
]

print("\n[Generating response...]")
response = llm.generate_response(
    user_message="Can I return a product I bought 2 weeks ago?",
    context_documents=context,
    company_name="TestCo"
)

print(f"\nSuccess: {response.success}")
print(f"Model Used: {response.model}")
print(f"Confidence: {response.confidence}")
print(f"Tokens: {response.tokens_used}")
print(f"\nResponse:\n{response.response}")
print("\n" + "=" * 60)
