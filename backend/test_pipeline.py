"""Final comprehensive test for all AI pipeline fixes."""
import sys, requests, json
sys.path.insert(0, ".")

BASE = "http://localhost:8000"
KEY = "wk_WME7ERpobn4ktaLvHCknxuPROyIk6t37tQczmKmNVkY"

# Create session
s = requests.post(f"{BASE}/api/widget/{KEY}/session", json={"customer_name":"Tester","customer_email":"t@t.com"})
sid = s.json()["session_id"]
print(f"Session: {sid}\n")

tests = [
    ("Greeting",          "Hello, how are you?",                   False),
    ("Product question",  "What products do you sell?",            False),
    ("Cancel request",    "Can I cancel my subscription?",         False),
    ("Refund request",    "I want a refund please",                False),
    ("Genuine anger",     "This is absolutely terrible, I will sue you and file a complaint with consumer protection!", True),
]

all_pass = True
for name, msg, expect_esc in tests:
    r = requests.post(f"{BASE}/api/widget/{KEY}/chat", json={"session_id": sid, "message": msg})
    d = r.json()
    esc = d.get("is_escalated", False)
    status = "PASS" if esc == expect_esc else "FAIL"
    if status == "FAIL": all_pass = False
    print(f"[{status}] {name}: escalated={esc} (expected={expect_esc}), confidence={d.get('confidence')}")
    print(f"      Response: {d.get('response','')[:100]}...")
    print()

print("=" * 50)
print(f"RESULT: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
