"""
WebSocket Connection Manager
Production-grade real-time communication for Behavioral Agentic AI

Features:
- Client connection tracking by ID and room (conversation)
- Broadcast to all clients or specific rooms
- Graceful disconnect handling
- Auto-cleanup of stale connections
- Thread-safe operations

Author: Behavioral Agentic AI Team
Version: 1.0.0
"""

import json
import logging
import asyncio
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time communication.
    
    Features:
    - Track active connections by client ID
    - Group connections by room (conversation_id)
    - Broadcast messages to all clients or specific rooms
    - Handle disconnections gracefully
    """
    
    def __init__(self):
        # All active connections: {client_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Room-based grouping: {room_id: set(client_ids)}
        self.rooms: Dict[str, Set[str]] = {}
        
        # Client metadata: {client_id: {...}}
        self.client_info: Dict[str, Dict] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        logger.info("🔌 WebSocket ConnectionManager initialized")
    
    async def connect(
        self, 
        websocket: WebSocket, 
        client_id: str,
        room_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            client_id: Unique identifier for the client
            room_id: Optional room to join (e.g., conversation_id)
            metadata: Optional client metadata (user_id, role, etc.)
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            await websocket.accept()
            
            async with self._lock:
                # Store connection
                self.active_connections[client_id] = websocket
                
                # Store metadata
                self.client_info[client_id] = {
                    "connected_at": datetime.now().isoformat(),
                    "room_id": room_id,
                    **(metadata or {})
                }
                
                # Join room if specified
                if room_id:
                    if room_id not in self.rooms:
                        self.rooms[room_id] = set()
                    self.rooms[room_id].add(client_id)
            
            logger.info(f"✅ Client {client_id} connected" + 
                       (f" to room {room_id}" if room_id else ""))
            
            # Send welcome message
            await self.send_personal_message(
                client_id,
                {
                    "type": "connection_established",
                    "client_id": client_id,
                    "room_id": room_id,
                    "message": "Connected to Behavioral AI"
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection failed for {client_id}: {e}")
            return False
    
    async def disconnect(self, client_id: str) -> None:
        """
        Handle client disconnection.
        
        Args:
            client_id: The client to disconnect
        """
        async with self._lock:
            # Remove from active connections
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            
            # Get room before removing client info
            room_id = self.client_info.get(client_id, {}).get("room_id")
            
            # Remove from room
            if room_id and room_id in self.rooms:
                self.rooms[room_id].discard(client_id)
                # Clean up empty rooms
                if not self.rooms[room_id]:
                    del self.rooms[room_id]
            
            # Remove client info
            if client_id in self.client_info:
                del self.client_info[client_id]
        
        logger.info(f"👋 Client {client_id} disconnected")
    
    async def send_personal_message(
        self, 
        client_id: str, 
        message: Dict[str, Any]
    ) -> bool:
        """
        Send a message to a specific client.
        
        Args:
            client_id: Target client ID
            message: Message to send (will be JSON encoded)
            
        Returns:
            True if sent successfully, False otherwise
        """
        websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_json(message)
                return True
            except Exception as e:
                logger.warning(f"⚠️ Failed to send to {client_id}: {e}")
                await self.disconnect(client_id)
        return False
    
    async def broadcast(self, message: Dict[str, Any]) -> int:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: Message to broadcast (will be JSON encoded)
            
        Returns:
            Number of clients that received the message
        """
        sent_count = 0
        disconnected = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"⚠️ Broadcast failed for {client_id}: {e}")
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)
        
        logger.debug(f"📡 Broadcast sent to {sent_count} clients")
        return sent_count
    
    async def broadcast_to_room(
        self, 
        room_id: str, 
        message: Dict[str, Any],
        exclude_client: Optional[str] = None
    ) -> int:
        """
        Broadcast a message to all clients in a specific room.
        
        Args:
            room_id: Target room ID
            message: Message to broadcast
            exclude_client: Optional client to exclude (e.g., sender)
            
        Returns:
            Number of clients that received the message
        """
        if room_id not in self.rooms:
            return 0
        
        sent_count = 0
        disconnected = []
        
        for client_id in self.rooms[room_id]:
            if exclude_client and client_id == exclude_client:
                continue
                
            websocket = self.active_connections.get(client_id)
            if websocket:
                try:
                    await websocket.send_json(message)
                    sent_count += 1
                except Exception as e:
                    logger.warning(f"⚠️ Room broadcast failed for {client_id}: {e}")
                    disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)
        
        logger.debug(f"📡 Room {room_id} broadcast sent to {sent_count} clients")
        return sent_count
    
    async def join_room(self, client_id: str, room_id: str) -> bool:
        """
        Add a client to a room.
        
        Args:
            client_id: Client to add
            room_id: Room to join
            
        Returns:
            True if successful
        """
        if client_id not in self.active_connections:
            return False
        
        async with self._lock:
            if room_id not in self.rooms:
                self.rooms[room_id] = set()
            self.rooms[room_id].add(client_id)
            
            # Update client info
            if client_id in self.client_info:
                self.client_info[client_id]["room_id"] = room_id
        
        logger.info(f"📥 Client {client_id} joined room {room_id}")
        return True
    
    async def leave_room(self, client_id: str, room_id: str) -> bool:
        """
        Remove a client from a room.
        
        Args:
            client_id: Client to remove
            room_id: Room to leave
            
        Returns:
            True if successful
        """
        async with self._lock:
            if room_id in self.rooms:
                self.rooms[room_id].discard(client_id)
                # Clean up empty rooms
                if not self.rooms[room_id]:
                    del self.rooms[room_id]
                    
            if client_id in self.client_info:
                self.client_info[client_id]["room_id"] = None
        
        logger.info(f"📤 Client {client_id} left room {room_id}")
        return True
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.active_connections)
    
    def get_room_count(self) -> int:
        """Get total number of active rooms."""
        return len(self.rooms)
    
    def get_room_members(self, room_id: str) -> List[str]:
        """Get list of client IDs in a room."""
        return list(self.rooms.get(room_id, set()))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "total_rooms": len(self.rooms),
            "rooms": {
                room_id: len(members) 
                for room_id, members in self.rooms.items()
            }
        }


# Global connection manager instance (singleton)
manager = ConnectionManager()


def get_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return manager
