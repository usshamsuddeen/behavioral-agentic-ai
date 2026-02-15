"""
Test escalation detection accuracy.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from app.services.escalation import check_escalation_triggers

print("\n" + "=" * 60)
print("    ESCALATION DETECTION TEST")
print("=" * 60)

# Test cases: (message, expected_escalation)
test_cases = [
    # SHOULD ESCALATE
    ("I want to speak to your manager immediately!", True),
    ("This is ridiculous! I demand a full refund!", True),
    ("I've had enough, I'm contacting my lawyer!", True),
    ("This is the worst service ever! Never again!", True),
    ("I WANT MY MONEY BACK RIGHT NOW!!!", True),
    ("I'm going to file a complaint with the BBB!", True),
    ("Let me talk to a real person, not a bot!", True),
    ("This is unbelievable, what a scam!", True),
    ("I need this resolved ASAP or I'm taking legal action!", True),
    ("Completely unacceptable! Get me your supervisor!", True),
    
    # SHOULD NOT ESCALATE
    ("Hi, I have a question about my order.", False),
    ("When will my package arrive?", False),
    ("Thank you for your help!", False),
    ("Can I exchange this for a different size?", False),
    ("How do I track my order?", False),
    ("What's your return policy?", False),
    ("I'd like to update my shipping address.", False),
    ("Is this item available in blue?", False),
    ("Can you check my order status?", False),
    ("What payment methods do you accept?", False),
]

correct = 0
total = len(test_cases)

for message, expected in test_cases:
    result = check_escalation_triggers(message, current_frustration=0.3)
    actual = result["should_escalate"]
    
    status = "OK" if actual == expected else "FAIL"
    if actual == expected:
        correct += 1
    
    indicator = "[ESCALATE]" if expected else "[NORMAL]"
    print(f"[{status}] {indicator} '{message[:45]}...'")
    if actual != expected:
        print(f"       Expected: {expected}, Got: {actual}")
        print(f"       Score: {result['trigger_score']}, Keywords: {result['keywords'][:2]}")

accuracy = (correct / total) * 100
print("\n" + "-" * 60)
print(f"Accuracy: {correct}/{total} = {accuracy:.1f}%")
print("=" * 60)

if accuracy >= 80:
    print("[SUCCESS] Target accuracy (80%) achieved!")
else:
    print(f"[WARN] Below target. Need {int((0.8 * total) - correct)} more correct.")
