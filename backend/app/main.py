"""
Behavioral Agentic AI - FastAPI Backend
Main Application Entry Point
"""

# ── Load .env FIRST, before any app modules read os.getenv() ──
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.middleware.rate_limit import RateLimitMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import json
import logging
import os

from app.database import engine, Base, SessionLocal
from app.api import conversations, messages, analytics, sentiment
from app.api import knowledge as knowledge_api
from app.api import ai_agent as ai_agent_api
from app.api import auth as auth_api
from app.api import onboarding as onboarding_api
from app.api import admin as admin_api
from app.api import widget_api
from app.api import settings_api
from app.api import widget_config_api
from app.websocket.manager import get_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_super_admin():
    """
    Create the platform Super Admin on first boot (idempotent).
    Credentials:  admin@behavioral-ai.com  /  admin@1122
    """
    # Import inside function to avoid circular-import issues
    from app.models.user import User, UserRole

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == "admin@behavioral-ai.com").first()
        if existing:
            logger.info("✅ Super Admin already exists (admin@behavioral-ai.com)")
            return

        admin = User(
            email="admin@behavioral-ai.com",
            name="Super Admin",
            full_name="Super Admin",
            avatar_initials="SA",
            role=UserRole.SUPER_ADMIN.value,
            status="active",
            is_active=True,
            onboarding_completed=True,
            onboarding_step=5,
        )
        admin.set_password("admin@1122")
        db.add(admin)
        db.commit()
        logger.info("🛡️  Super Admin created  →  admin@behavioral-ai.com / admin@1122")
    except Exception as e:
        logger.error(f"Failed to seed Super Admin: {e}")
        db.rollback()
    finally:
        db.close()


# Create database tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - create tables on startup"""
    Base.metadata.create_all(bind=engine,checkfirst=True)
    ensure_super_admin()
    logger.info("🚀 Behavioral Agentic AI started")
    yield
    logger.info("👋 Behavioral Agentic AI shutdown")



# Initialize FastAPI application
app = FastAPI(
    title="Behavioral Agentic AI",
    description="Sentiment-Aware Escalation System for Multilingual Customer Support",
    version="3.0.0",
    lifespan=lifespan
)

# CORS Configuration - Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",     # Next.js default
        "http://localhost:5500",     # Live Server
        "http://127.0.0.1:5500",     # Live Server alt
        "http://localhost:8080",     # Alternative
        "null",                       # For file:// protocol
        "*"                           # Allow all for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FR-7.2.5: Rate Limiting — 60 req/min widget, 120 req/min dashboard
app.add_middleware(RateLimitMiddleware)

# Include API Routers
app.include_router(auth_api.router)  # Auth routes (no prefix - uses /api/auth)
app.include_router(conversations.router, prefix="/api", tags=["Conversations"])
app.include_router(messages.router, prefix="/api", tags=["Messages"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(sentiment.router, prefix="/api", tags=["Sentiment"])
app.include_router(knowledge_api.router, tags=["Knowledge Base"])
app.include_router(ai_agent_api.router, tags=["AI Agent"])
app.include_router(onboarding_api.router)  # Zone 2: Onboarding Wizard
app.include_router(admin_api.router)        # Zone 4: Super Admin
app.include_router(widget_api.router)       # Zone 6: Customer Widget
app.include_router(settings_api.router)     # Zone 3: Settings & Team (FR-3.6)
app.include_router(widget_config_api.router) # Zone 3: Widget Config (FR-3.5)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Behavioral Agentic AI",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "websocket": "/ws/{client_id}"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring"""
    ws_manager = get_manager()
    return {
        "status": "healthy",
        "service": "behavioral-agentic-ai",
        "database": "connected",
        "websocket": {
            "connections": ws_manager.get_connection_count(),
            "rooms": ws_manager.get_room_count()
        }
    }


# ═══════════════════════════════════════════════════════════════════
# WEBSOCKET ENDPOINT - Real-Time Communication
# ═══════════════════════════════════════════════════════════════════

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time communication.
    
    Args:
        client_id: Unique client identifier (e.g., user_id or session_id)
        
    Query Params:
        room: Optional room to join (e.g., conversation_id)
    
    Message Types (incoming):
        - join_room: {"type": "join_room", "room_id": "conv_123"}
        - leave_room: {"type": "leave_room", "room_id": "conv_123"}
        - message: {"type": "message", "content": "...", "room_id": "conv_123"}
        - ping: {"type": "ping"}
    
    Message Types (outgoing):
        - connection_established: Initial connection confirmation
        - new_message: Real-time message notification
        - sentiment_update: Sentiment analysis result
        - escalation_alert: Escalation notification
        - pong: Response to ping
    """
    ws_manager = get_manager()
    
    # Get room from query params if provided
    room_id = websocket.query_params.get("room")
    
    # Connect client
    connected = await ws_manager.connect(
        websocket=websocket,
        client_id=client_id,
        room_id=room_id,
        metadata={"user_agent": websocket.headers.get("user-agent", "unknown")}
    )
    
    if not connected:
        return
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                msg_type = message.get("type", "unknown")
                
                # Handle different message types
                if msg_type == "ping":
                    # Respond to ping
                    await ws_manager.send_personal_message(
                        client_id,
                        {"type": "pong", "timestamp": message.get("timestamp")}
                    )
                    
                elif msg_type == "join_room":
                    # Join a conversation room
                    room = message.get("room_id")
                    if room:
                        await ws_manager.join_room(client_id, room)
                        await ws_manager.send_personal_message(
                            client_id,
                            {"type": "room_joined", "room_id": room}
                        )
                        
                elif msg_type == "leave_room":
                    # Leave a conversation room
                    room = message.get("room_id")
                    if room:
                        await ws_manager.leave_room(client_id, room)
                        await ws_manager.send_personal_message(
                            client_id,
                            {"type": "room_left", "room_id": room}
                        )
                        
                elif msg_type == "message":
                    # Broadcast message to room
                    room = message.get("room_id")
                    content = message.get("content")
                    if room and content:
                        await ws_manager.broadcast_to_room(
                            room,
                            {
                                "type": "new_message",
                                "sender_id": client_id,
                                "content": content,
                                "room_id": room
                            },
                            exclude_client=client_id  # Don't echo back to sender
                        )
                        
                else:
                    # Echo unknown message types for debugging
                    await ws_manager.send_personal_message(
                        client_id,
                        {"type": "echo", "received": message}
                    )
                    
            except json.JSONDecodeError:
                await ws_manager.send_personal_message(
                    client_id,
                    {"type": "error", "message": "Invalid JSON"}
                )
                
    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id)
        logger.info(f"🔌 Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error for {client_id}: {e}")
        await ws_manager.disconnect(client_id)


@app.get("/api/websocket/stats")
async def websocket_stats():
    """Get WebSocket connection statistics"""
    ws_manager = get_manager()
    return ws_manager.get_stats()


# ═══════════════════════════════════════════════════════════════════
# WIDGET EMBED SCRIPT — Zone 6 (FR-6.1.1)
# ═══════════════════════════════════════════════════════════════════

WIDGET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "widget")

@app.get("/widget/embed.js")
async def serve_embed_js():
    """Serve the embeddable widget JavaScript — FR-6.1.1"""
    embed_path = os.path.join(WIDGET_DIR, "embed.js")
    if not os.path.exists(embed_path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Widget script not found")
    return FileResponse(
        embed_path,
        media_type="application/javascript",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600"
        }
    )


# ═══════════════════════════════════════════════════════════════════
# FRONTEND STATIC FILES — Serve dashboard UI
# MUST be mounted LAST so API routes take priority
# ═══════════════════════════════════════════════════════════════════

# Try multiple paths: Docker (/app/frontend) → Local (../../frontend relative to this file)
_possible_frontend_paths = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend"),  # local dev
    "/app/frontend",  # Docker container
]
FRONTEND_DIR = next((p for p in _possible_frontend_paths if os.path.isdir(p)), None)

if FRONTEND_DIR:
    # Serve static assets (CSS, JS, images)
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
    app.mount("/widget", StaticFiles(directory=os.path.join(FRONTEND_DIR, "widget")), name="widget-static")

    # Serve HTML pages
    @app.get("/login")
    @app.get("/pages/login.html")
    async def serve_login():
        return FileResponse(os.path.join(FRONTEND_DIR, "pages", "login.html"))

    @app.get("/signup")
    @app.get("/pages/signup.html")
    async def serve_signup():
        return FileResponse(os.path.join(FRONTEND_DIR, "pages", "signup.html"))

    @app.get("/dashboard")
    @app.get("/pages/client-dashboard.html")
    async def serve_dashboard():
        return FileResponse(os.path.join(FRONTEND_DIR, "pages", "client-dashboard.html"))

    @app.get("/onboarding")
    @app.get("/pages/onboarding.html")
    async def serve_onboarding():
        return FileResponse(os.path.join(FRONTEND_DIR, "pages", "onboarding.html"))

    @app.get("/escalations")
    @app.get("/pages/escalations.html")
    async def serve_escalations():
        return FileResponse(os.path.join(FRONTEND_DIR, "pages", "escalations.html"))

    @app.get("/knowledge")
    @app.get("/pages/knowledge-base.html")
    async def serve_knowledge():
        return FileResponse(os.path.join(FRONTEND_DIR, "pages", "knowledge-base.html"))

    @app.get("/admin")
    @app.get("/pages/admin.html")
    async def serve_admin():
        return FileResponse(os.path.join(FRONTEND_DIR, "pages", "admin.html"))

    @app.get("/widget-management")
    @app.get("/pages/widget-management.html")
    async def serve_widget_management():
        return FileResponse(os.path.join(FRONTEND_DIR, "pages", "widget-management.html"))

    @app.get("/widget-test")
    @app.get("/widget-test.html")
    async def serve_widget_test():
        return FileResponse(os.path.join(FRONTEND_DIR, "widget-test.html"))

    @app.get("/ui")
    async def serve_landing():
        """Serve the main landing / index page"""
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    logger.info(f"📁 Frontend served from: {FRONTEND_DIR}")
else:
    logger.warning(f"⚠️ Frontend directory not found: {FRONTEND_DIR}")

