"""
Escalation Trigger Accuracy Testing
Tests escalation detection system against known scenarios
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.escalation import check_escalation_triggers, calculate_escalation_priority


# Test scenarios: (text, should_escalate, expected_priority)
TEST_SCENARIOS = [
    # Should Escalate - Legal Threats
    ("I'm going to contact my lawyer about this", True, "urgent"),
    ("You'll hear from my attorney", True, "urgent"),
    ("This is illegal and I'm reporting you", True, "urgent"),
    
    # Should Escalate - Social Media Threats
    ("I'm posting this on Twitter right now", True, "high"),
    ("Everyone on Facebook will know about this terrible service", True, "high"),
    ("I'm leaving a 1-star review everywhere", True, "high"),
    
    # Should Escalate - Extreme Frustration
    ("THIS IS RIDICULOUS!!! I'VE HAD ENOUGH!!!", True, "high"),
    ("I DEMAND TO SPEAK TO YOUR MANAGER NOW!!!", True, "urgent"),
    ("UNACCEPTABLE!!! WORST SERVICE EVER!!!", True, "high"),
    
    # Should Escalate - Management Request
    ("Can I speak to your supervisor please?", True, "high"),
    ("I need to talk to someone higher up", True, "high"),
    ("Transfer me to your manager immediately", True, "urgent"),
    
    # Should Escalate - Refund/Cancel Demands
    ("I want a full refund right now", True, "high"),
    ("Cancel my order immediately", True, "normal"),
    ("This is a scam, give me my money back", True, "urgent"),
    
    # Should NOT Escalate - Normal Inquiries
    ("Can you help me track my order?", False, "low"),
    ("I have a question about shipping", False, "low"),
    ("When will my package arrive?", False, "low"),
    
    # Should NOT Escalate - Positive Feedback
    ("Thank you for your help!", False, "low"),
    ("Great service, very satisfied", False, "low"),
    ("This product is exactly what I needed", False, "low"),
    
    # Should NOT Escalate - Neutral Requests
    ("I need more information about this", False, "low"),
    ("Can you explain how this works?", False, "low"),
    ("What are my options?", False, "normal"),
    
    # Should NOT Escalate - Minor Complaints
    ("The delivery was a bit slow", False, "normal"),
    ("It's okay but not exactly what I expected", False, "low"),
    ("There's a small issue with the packaging", False, "normal"),
    
    # Edge Cases - Borderline
    ("I'm not happy with this at all", False, "normal"),
    ("This is disappointing", False, "normal"),
    ("I expected better quality", False, "normal"),
]


class TestEscalationAccuracy:
    """Test suite for escalation trigger detection"""
    
    def test_individual_scenarios(self):
        """Test each scenario individually"""
        correct_escalation = 0
        correct_priority = 0
        total = len(TEST_SCENARIOS)
        
        errors = []
        
        print("\n" + "=" * 70)
        print("🚨 ESCALATION TRIGGER ACCURACY TEST")
        print("=" * 70)
        
        for text, should_escalate, expected_priority in TEST_SCENARIOS:
            result = check_escalation_triggers(text, current_frustration=0.5)
            
            # Check escalation decision
            actual_escalate = result['should_escalate']
            if actual_escalate == should_escalate:
                correct_escalation += 1
                emoji = "✅"
            else:
                emoji = "❌"
                errors.append({
                    'text': text,
                    'expected_escalate': should_escalate,
                    'actual_escalate': actual_escalate,
                    'expected_priority': expected_priority,
                    'trigger_score': result['trigger_score']
                })
            
            # Calculate priority for comparison
            if actual_escalate:
                priority = calculate_escalation_priority(
                    sentiment_score=0.3,
                    frustration_level=0.5,
                    message_count=5,
                    has_triggers=True
                )
                
                # Priority match (only check if actually escalated)
                if priority == expected_priority or \
                   (priority == "urgent" and expected_priority == "high") or \
                   (priority == "high" and expected_priority == "urgent"):
                    correct_priority += 1
        
        # Calculate accuracy
        escalation_accuracy = correct_escalation / total
        priority_accuracy = correct_priority / sum(1 for _, should, _ in TEST_SCENARIOS if should)
        
        print(f"\n📊 Results:")
        print(f"   Total Scenarios: {total}")
        print(f"   Correct Escalation Decisions: {correct_escalation}/{total}")
        print(f"   Escalation Accuracy: {escalation_accuracy * 100:.2f}%")
        print(f"   Priority Accuracy (for escalated): {priority_accuracy * 100:.2f}%")
        
        if errors:
            print(f"\n❌ Errors ({len(errors)}):")
            for error in errors[:5]:  # Show first 5 errors
                print(f"\n   Text: '{error['text']}'")
                print(f"   Expected Escalate: {error['expected_escalate']}")
                print(f"   Actual Escalate: {error['actual_escalate']}")
                print(f"   Trigger Score: {error['trigger_score']}")
        
        print("\n" + "=" * 70)
        
        # Assert minimum accuracy
        assert escalation_accuracy >= 0.75, \
            f"Escalation accuracy {escalation_accuracy*100:.2f}% below 75% threshold"
    
    def test_legal_keywords(self):
        """Test detection of legal threat keywords"""
        legal_threats = [
            "I'm calling my lawyer",
            "You'll be hearing from my attorney",
            "I'm taking legal action",
            "This is going to court",
            "I'll sue you for this"
        ]
        
        for threat in legal_threats:
            result = check_escalation_triggers(threat)
            assert result['should_escalate'], f"Failed to escalate legal threat: {threat}"
            assert 'lawyer' in str(result['keywords']).lower() or \
                   'attorney' in str(result['keywords']).lower() or \
                   'legal' in str(result['keywords']).lower() or \
                   'sue' in str(result['keywords']).lower()
    
    def test_social_media_keywords(self):
        """Test detection of social media threat keywords"""
        social_threats = [
            "I'm posting this on Twitter",
            "Everyone on Facebook will see this",
            "I'm writing a review on Yelp",
            "This is going viral on social media"
        ]
        
        for threat in social_threats:
            result = check_escalation_triggers(threat)
            assert result['should_escalate'], f"Failed to escalate social media threat: {threat}"
    
    def test_caps_lock_detection(self):
        """Test caps lock (shouting) detection"""
        result = check_escalation_triggers("THIS IS COMPLETELY UNACCEPTABLE!!!")
        assert result['is_trigger'], "Failed to detect caps lock shouting"
        assert any('caps' in reason.lower() for reason in result['reasons'])
    
    def test_normal_messages_noescalate(self):
        """Test that normal messages don't trigger escalation"""
        normal_messages = [
            "Hello, can you help me?",
            "I have a question about my order",
            "Thank you for your assistance",
            "When will this be delivered?"
        ]
        
        for message in normal_messages:
            result = check_escalation_triggers(message)
            assert not result['should_escalate'], \
                f"Incorrectly escalated normal message: {message}"
    
    def test_frustration_amplification(self):
        """Test that high frustration amplifies escalation"""
        borderline_message = "I'm not happy about this"
        
        # Low frustration - should not escalate
        result_low = check_escalation_triggers(borderline_message, current_frustration=0.3)
        
        # High frustration - should escalate or have higher score
        result_high = check_escalation_triggers(borderline_message, current_frustration=0.8)
        
        assert result_high['trigger_score'] > result_low['trigger_score'], \
            "High frustration should increase trigger score"
    
    def test_priority_calculation(self):
        """Test escalation priority levels"""
        # Urgent scenario
        priority_urgent = calculate_escalation_priority(
            sentiment_score=0.1,  # Very negative
            frustration_level=0.9,  # Very frustrated
            message_count=15,  # Long conversation
            has_triggers=True  # Has escalation keywords
        )
        assert priority_urgent in ["urgent", "high"], \
            f"Expected high/urgent priority, got {priority_urgent}"
        
        # Normal scenario
        priority_normal = calculate_escalation_priority(
            sentiment_score=0.6,  # Neutral-positive
            frustration_level=0.3,  # Low frustration
            message_count=3,  # Short conversation
            has_triggers=False
        )
        assert priority_normal in ["low", "normal"], \
            f"Expected low/normal priority, got {priority_normal}"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
