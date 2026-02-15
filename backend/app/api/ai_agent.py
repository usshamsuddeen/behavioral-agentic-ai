"""
AI Agent API for Behavioral Agentic AI
REST API endpoints for AI-powered auto-responses

Endpoints:
- POST /ai/process: Process a message and get AI response
- POST /ai/chat: Simple chat interface
- GET /ai/info: Get AI agent information
- GET /ai/health: Check AI service health

Author: Behavioral Agentic AI Team
Version: 1.0.0
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.ai.agent import get_ai_agent, AgentContext

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/ai", tags=["AI Agent"])

# Default client ID
DEFAULT_CLIENT_ID = "default_client"


# ============ Request/Response Models ============

class MessageHistoryItem(BaseModel):
    """Single message in conversation history."""
    content: str = Field(..., description="Message content")
    sender_type: str = Field("customer", description="Sender type: customer or agent")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class ProcessMessageRequest(BaseModel):
    """Request to process a customer message."""
    message: str = Field(..., description="Customer message")
    conversation_id: str = Field("default", description="Conversation ID")
    client_id: Optional[str] = Field(None, description="Client ID")
    conversation_history: List[MessageHistoryItem] = Field(
        default_factory=list, 
        description="Previous messages"
    )
    company_name: str = Field("Our Company", description="Company name")
    company_guidelines: Optional[str] = Field(None, description="Response guidelines")
    current_frustration: float = Field(0.0, ge=0.0, le=1.0, description="Current frustration level")


class ChatRequest(BaseModel):
    """Simple chat request."""
    message: str = Field(..., description="User message")
    client_id: Optional[str] = Field(None, description="Client ID")
    conversation_id: str = Field("default", description="Conversation ID")


class AgentResponse(BaseModel):
    """AI agent response."""
    success: bool
    action: str
    response: str
    sentiment: dict
    escalation: dict
    confidence: float
    requires_human: bool
    context_used: List[str] = []
    metadata: dict = {}


class ChatResponse(BaseModel):
    """Simple chat response."""
    response: str
    sentiment: str
    confidence: float
    requires_human: bool


class AgentInfoResponse(BaseModel):
    """AI agent info response."""
    agent_available: bool
    llm_available: bool
    llm_model: str
    escalation_threshold: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    services: dict


# ============ API Endpoints ============

@router.post("/process", response_model=AgentResponse)
async def process_message(request: ProcessMessageRequest):
    """
    Process a customer message with full AI pipeline.
    
    This endpoint:
    1. Analyzes sentiment
    2. Checks escalation triggers
    3. Retrieves relevant knowledge
    4. Generates AI response
    5. Evaluates confidence
    
    - **message**: Customer message to process
    - **conversation_id**: Conversation identifier
    - **client_id**: Client identifier for knowledge base
    - **conversation_history**: Previous messages for context
    - **company_name**: Company name for personalization
    - **company_guidelines**: Response guidelines
    - **current_frustration**: Customer frustration level (0-1)
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")
    
    try:
        agent = get_ai_agent()
        
        # Build context
        context = AgentContext(
            client_id=request.client_id or DEFAULT_CLIENT_ID,
            conversation_id=request.conversation_id,
            user_message=request.message,
            conversation_history=[
                {
                    "content": m.content,
                    "sender_type": m.sender_type,
                    "timestamp": m.timestamp
                }
                for m in request.conversation_history
            ],
            company_name=request.company_name,
            company_guidelines=request.company_guidelines,
            current_frustration=request.current_frustration
        )
        
        # Process message
        result = agent.process_message(context)
        
        return AgentResponse(
            success=True,
            action=result.action.value,
            response=result.response,
            sentiment=result.sentiment,
            escalation=result.escalation,
            confidence=result.confidence,
            requires_human=result.requires_human,
            context_used=result.context_used,
            metadata=result.metadata
        )
        
    except Exception as e:
        logger.error(f"❌ Process message failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def simple_chat(request: ChatRequest):
    """
    Simple chat interface for quick AI responses.
    
    Streamlined endpoint for basic chat interactions.
    
    - **message**: User message
    - **client_id**: Client identifier (optional)
    - **conversation_id**: Conversation ID (optional)
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")
    
    try:
        agent = get_ai_agent()
        
        context = AgentContext(
            client_id=request.client_id or DEFAULT_CLIENT_ID,
            conversation_id=request.conversation_id,
            user_message=request.message
        )
        
        result = agent.process_message(context)
        
        return ChatResponse(
            response=result.response,
            sentiment=result.sentiment.get("sentiment", "neutral"),
            confidence=result.confidence,
            requires_human=result.requires_human
        )
        
    except Exception as e:
        logger.error(f"❌ Chat failed: {e}")
        return ChatResponse(
            response="I apologize, but I'm experiencing technical difficulties. Please try again or contact support.",
            sentiment="neutral",
            confidence=0.0,
            requires_human=True
        )


@router.get("/info", response_model=AgentInfoResponse)
async def get_agent_info():
    """
    Get AI agent configuration and status.
    
    Returns information about the AI agent's capabilities
    and current configuration.
    """
    try:
        agent = get_ai_agent()
        info = agent.get_agent_info()
        
        return AgentInfoResponse(
            agent_available=True,
            llm_available=info.get("llm_available", False),
            llm_model=info.get("llm_model", "unknown"),
            escalation_threshold=info.get("escalation_threshold", 0.5)
        )
        
    except Exception as e:
        logger.error(f"❌ Get agent info failed: {e}")
        return AgentInfoResponse(
            agent_available=False,
            llm_available=False,
            llm_model="unknown",
            escalation_threshold=0.5
        )


@router.get("/health", response_model=HealthResponse)
async def check_health():
    """
    Check AI service health status.
    
    Verifies that all AI components are operational.
    """
    services = {
        "agent": False,
        "llm": False,
        "embedding": False,
        "vector_store": False
    }
    
    try:
        # Check agent
        from app.ai.agent import get_ai_agent
        agent = get_ai_agent()
        services["agent"] = True
        
        # Check LLM
        from app.ai.llm import get_llm_service
        llm = get_llm_service()
        services["llm"] = llm.is_available()
        
        # Check embeddings
        from app.ai.embeddings import is_model_available
        services["embedding"] = is_model_available()
        
        # Check vector store
        from app.ai.vector_store import get_vector_store
        vs = get_vector_store()
        services["vector_store"] = True
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
    
    # Determine overall status
    all_healthy = all(services.values())
    some_healthy = any(services.values())
    
    if all_healthy:
        status = "healthy"
    elif some_healthy:
        status = "degraded"
    else:
        status = "unhealthy"
    
    return HealthResponse(
        status=status,
        services=services
    )


@router.post("/test")
async def test_rag_pipeline(
    query: str = Query(..., description="Test query"),
    client_id: Optional[str] = Query(None, description="Client ID")
):
    """
    Test the RAG pipeline components.
    
    Useful for debugging and verifying the setup.
    """
    client = client_id or DEFAULT_CLIENT_ID
    results = {
        "query": query,
        "client_id": client,
        "steps": {}
    }
    
    try:
        # Step 1: Test embedding
        from app.ai.embeddings import get_embedding_service
        emb = get_embedding_service()
        embedding = emb.embed_text(query)
        results["steps"]["embedding"] = {
            "success": True,
            "dimension": len(embedding)
        }
    except Exception as e:
        results["steps"]["embedding"] = {"success": False, "error": str(e)}
    
    try:
        # Step 2: Test retrieval
        from app.ai.retrieval import get_retrieval_service
        ret = get_retrieval_service()
        docs = ret.retrieve(client, query, top_k=3)
        results["steps"]["retrieval"] = {
            "success": True,
            "documents_found": len(docs),
            "top_match": docs[0].text[:200] if docs else None
        }
    except Exception as e:
        results["steps"]["retrieval"] = {"success": False, "error": str(e)}
    
    try:
        # Step 3: Test LLM
        from app.ai.llm import get_llm_service
        llm = get_llm_service()
        results["steps"]["llm"] = {
            "available": llm.is_available(),
            "model": llm.model
        }
    except Exception as e:
        results["steps"]["llm"] = {"success": False, "error": str(e)}
    
    return results
