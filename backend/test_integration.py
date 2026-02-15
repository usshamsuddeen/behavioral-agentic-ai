"""
Frontend-Backend Integration Test
Tests all API endpoints that the frontend relies on
"""
import sys
import requests
sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://localhost:8000"

print("\n" + "=" * 60)
print("    FRONTEND-BACKEND INTEGRATION TEST")
print("=" * 60)


def test_endpoint(name, method, endpoint, expected_status=200, json_data=None):
    """Test an API endpoint."""
    url = f"{API_BASE}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=json_data, timeout=10)
        else:
            response = requests.request(method, url, json=json_data, timeout=10)
        
        status = response.status_code
        success = status == expected_status or status in [200, 201]
        
        icon = "[OK]" if success else "[FAIL]"
        print(f"{icon} {name}: {method} {endpoint} -> {status}")
        
        return success, response.json() if response.text else {}
        
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] {name}: Connection refused (backend not running?)")
        return False, {}
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        return False, {}


def run_tests():
    results = []
    
    print("\n[1] Core Health Endpoints")
    print("-" * 40)
    
    # Root
    ok, _ = test_endpoint("Root", "GET", "/")
    results.append(ok)
    
    # Health
    ok, _ = test_endpoint("Health Check", "GET", "/api/health")
    results.append(ok)
    
    print("\n[2] AI Agent Endpoints")
    print("-" * 40)
    
    # AI Health
    ok, _ = test_endpoint("AI Health", "GET", "/api/ai/health")
    results.append(ok)
    
    # AI Info
    ok, _ = test_endpoint("AI Info", "GET", "/api/ai/info")
    results.append(ok)
    
    # AI Chat
    ok, data = test_endpoint("AI Chat", "POST", "/api/ai/chat", json_data={
        "message": "What is your return policy?",
        "client_id": "test_client"
    })
    results.append(ok)
    if ok and data:
        print(f"       Response: {data.get('response', '')[:80]}...")
    
    print("\n[3] Knowledge Base Endpoints")
    print("-" * 40)
    
    # Stats
    ok, data = test_endpoint("KB Stats", "GET", "/api/knowledge/stats?client_id=default_client")
    results.append(ok)
    if ok and data:
        print(f"       Documents: {data.get('total_documents', 0)}")
    
    # Documents list
    ok, _ = test_endpoint("KB Documents", "GET", "/api/knowledge/documents?client_id=default_client")
    results.append(ok)
    
    # Search
    ok, data = test_endpoint("KB Search", "POST", "/api/knowledge/search", json_data={
        "query": "return policy",
        "top_k": 3,
        "client_id": "default_client"
    })
    results.append(ok)
    if ok and data:
        print(f"       Results: {data.get('results_count', 0)}")
    
    print("\n[4] WebSocket Endpoint")
    print("-" * 40)
    
    # WS Stats
    ok, _ = test_endpoint("WS Stats", "GET", "/api/websocket/stats")
    results.append(ok)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 60)
    print(f"    RESULTS: {passed}/{total} endpoints working")
    print("=" * 60)
    
    if passed == total:
        print("[SUCCESS] All endpoints operational!")
    elif passed > 0:
        print("[PARTIAL] Some endpoints need attention")
    else:
        print("[FAIL] Backend may not be running - start with: uvicorn app.main:app --reload")
    
    return passed == total


if __name__ == "__main__":
    run_tests()
