"""
API Endpoint Tests
Tests for all REST API endpoints
"""

import pytest
from fastapi import status


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns service info"""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Behavioral Agentic AI"
        assert data["status"] == "running"
        assert "websocket" in data
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "websocket" in data


class TestConversationEndpoints:
    """Test conversation API endpoints"""
    
    def test_create_conversation(self, client, sample_conversation):
        """Test creating a new conversation"""
        response = client.post("/api/conversations", json=sample_conversation)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["customer_name"] == sample_conversation["customer_name"]
        assert "id" in data
    
    def test_get_conversations(self, client):
        """Test getting all conversations"""
        response = client.get("/api/conversations")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_conversation_not_found(self, client):
        """Test getting non-existent conversation"""
        response = client.get("/api/conversations/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestMessageEndpoints:
    """Test message API endpoints"""
    
    def test_send_message_to_conversation(self, client, sample_conversation, sample_message):
        """Test sending a message to a conversation"""
        # First create a conversation
        conv_response = client.post("/api/conversations", json=sample_conversation)
        conv_id = conv_response.json()["id"]
        
        # Send message
        response = client.post(f"/api/conversations/{conv_id}/messages", json=sample_message)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["content"] == sample_message["content"]
        assert "sentiment_label" in data
        assert "sentiment_score" in data


class TestSentimentEndpoints:
    """Test sentiment analysis API endpoints"""
    
    def test_analyze_sentiment(self, client):
        """Test sentiment analysis endpoint"""
        response = client.post("/api/sentiment/analyze", json={
            "text": "I am very happy with this service!",
            "language": "en"
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["sentiment"] == "positive"
        assert "score" in data
    
    def test_analyze_negative_sentiment(self, client):
        """Test negative sentiment detection"""
        response = client.post("/api/sentiment/analyze", json={
            "text": "This is terrible and I am furious!",
            "language": "en"
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["sentiment"] == "negative"
    
    def test_detect_language(self, client):
        """Test language detection endpoint"""
        response = client.post("/api/sentiment/detect-language", json={
            "text": "Bonjour, comment ça va?"
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "language" in data


class TestAnalyticsEndpoints:
    """Test analytics API endpoints"""
    
    def test_get_metrics(self, client):
        """Test getting dashboard metrics"""
        response = client.get("/api/analytics/metrics")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_conversations" in data
        assert "active_conversations" in data
    
    def test_get_sentiment_trends(self, client):
        """Test getting sentiment trends"""
        response = client.get("/api/analytics/sentiment-trends")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


class TestWebhookEndpoints:
    """Test webhook API endpoints"""
    
    def test_generic_webhook(self, client):
        """Test generic webhook endpoint"""
        response = client.post("/api/webhooks/generic", json={
            "external_id": "test_123",
            "content": "Hello, I need help with my order",
            "sender_name": "Test User",
            "language": "en"
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "processed"
        assert "sentiment_analysis" in data
    
    def test_zendesk_webhook(self, client):
        """Test Zendesk webhook endpoint"""
        response = client.post("/api/webhooks/zendesk", json={
            "ticket_id": "12345",
            "subject": "Order Issue",
            "description": "I haven't received my order and I'm upset",
            "status": "new",
            "priority": "high"
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["source"] == "zendesk"
        assert "sentiment_analysis" in data


class TestWebSocketStats:
    """Test WebSocket statistics endpoint"""
    
    def test_websocket_stats(self, client):
        """Test WebSocket stats endpoint"""
        response = client.get("/api/websocket/stats")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_connections" in data
        assert "total_rooms" in data
