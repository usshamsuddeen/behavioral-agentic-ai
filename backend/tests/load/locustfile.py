"""
Load Testing Configuration for Behavioral Agentic AI
Tests system performance under concurrent load
"""

from locust import HttpUser, task, between, events
from locust.env import Environment
import random
import json


class CustomerUser(HttpUser):
    """Simulates a customer using the chat system"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    host = "http://localhost:8000"
    
    def on_start(self):
        """Called when a user starts"""
        # Create a new conversation for this user
        response = self.client.post("/api/conversations", json={
            "customer_name": f"LoadTest User {self.environment.runner.user_count}",
            "customer_email": f"loadtest{random.randint(1000,9999)}@example.com",
            "source": "web_chat"
        })
        
        if response.status_code == 200:
            self.conversation_id = response.json().get("id")
        else:
            self.conversation_id = 1  # Fallback
    
    @task(5)
    def send_message(self):
        """Send a customer message (most common action)"""
        messages = [
            "Hello, I need help with my order",
            "Can you track my shipment?",
            "I want to return this product",
            "The quality is not what I expected",
            "When will my order arrive?",
            "I'm having trouble with my payment",
            "This is taking too long!",
            "Your service is excellent, thank you!",
            "I need to speak with a manager",
            "Can you help me?",
            "This is unacceptable!",
            "Great experience so far",
        ]
        
        message = random.choice(messages)
        
        self.client.post(f"/api/conversations/{self.conversation_id}/messages", json={
            "text": message,
            "sender": "customer"
        }, name="/api/conversations/[id]/messages")
    
    @task(2)
    def get_conversation(self):
        """Retrieve conversation details"""
        self.client.get(
            f"/api/conversations/{self.conversation_id}",
            name="/api/conversations/[id]"
        )
    
    @task(1)
    def analyze_sentiment(self):
        """Direct sentiment analysis API call"""
        test_texts = [
            "I love this product!",
            "This is terrible",
            "It's okay, nothing special",
            "Best purchase ever!",
            "I want my money back",
        ]
        
        self.client.post("/api/sentiment/analyze", json={
            "text": random.choice(test_texts),
            "language": random.choice(["en", "es", "fr", "de", "it", "nl"])
        })


class AgentUser(HttpUser):
    """Simulates an agent using the dashboard"""
    
    wait_time = between(2, 5)
    host = "http://localhost:8000"
    
    @task(3)
    def view_dashboard(self):
        """View dashboard metrics"""
        self.client.get("/api/analytics/metrics")
    
    @task(2)
    def list_conversations(self):
        """List active conversations"""
        self.client.get("/api/conversations?status=active&limit=20")
    
    @task(1)
    def check_escalations(self):
        """Check escalated conversations"""
        self.client.get("/api/conversations?escalated=true&limit=10")
    
    @task(1)
    def view_conversation_details(self):
        """View specific conversation"""
        conv_id = random.randint(1, 50)
        self.client.get(f"/api/conversations/{conv_id}", name="/api/conversations/[id]")


# Custom event listeners for reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    print("\n🚀 Starting Load Test...")
    print(f"   Target: {environment.host}")
    print(f"   Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops"""
    stats = environment.stats
    
    print("\n" + "=" * 70)
    print("📊 LOAD TEST RESULTS")
    print("=" * 70)
    
    print(f"\n📈 Overall Statistics:")
    print(f"   Total Requests: {stats.total.num_requests}")
    print(f"   Total Failures: {stats.total.num_failures}")
    print(f"   Failure Rate: {stats.total.fail_ratio * 100:.2f}%")
    print(f"   Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"   Median Response Time: {stats.total.median_response_time:.2f}ms")
    print(f"   95th Percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"   99th Percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"   Requests/sec: {stats.total.total_rps:.2f}")
    
    print(f"\n🎯 Performance Assessment:")
    
    # Check against targets
    avg_time = stats.total.avg_response_time
    failure_rate = stats.total.fail_ratio
    
    if avg_time < 3000 and failure_rate < 0.05:
        print("   ✅ EXCELLENT: Meets all performance targets")
    elif avg_time < 5000 and failure_rate < 0.10:
        print("   ⚠️ ACCEPTABLE: Meets basic performance requirements")
    else:
        print("   ❌ NEEDS IMPROVEMENT: Performance below targets")
    
    print(f"\n📋 Detailed Endpoint Performance:")
    print(f"   {'Endpoint':<40} {'Requests':<10} {'Avg(ms)':<10} {'Failures':<10}")
    print(f"   {'-'*70}")
    
    for name, entry in sorted(stats.entries.items(), key=lambda x: x[1].num_requests, reverse=True):
        if isinstance(name, tuple):
            endpoint = name[1]
        else:
            endpoint = name
            
        print(f"   {endpoint:<40} {entry.num_requests:<10} "
              f"{entry.avg_response_time:<10.2f} {entry.num_failures:<10}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("⚠️ Run this file using the locust command:")
    print("   locust -f tests/load/locustfile.py --host=http://localhost:8000")
    print("\nOptions:")
    print("   --users 100 --spawn-rate 10   # 100 concurrent users, spawn 10/sec")
    print("   --headless --run-time 5m      # Run for 5 minutes without web UI")
