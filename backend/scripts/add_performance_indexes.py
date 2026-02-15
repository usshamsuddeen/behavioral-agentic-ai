"""
Database Migration Script - Add Performance Indexes
Optimizes database queries for production load
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, Index, text
from app.database import DATABASE_URL, Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_performance_indexes():
    """Add database indexes for frequently queried fields"""
    
    engine = create_engine(DATABASE_URL)
    
    logger.info("Adding performance indexes to database...")
    
    with engine.connect() as conn:
        try:
            # Conversation indexes
            logger.info("Creating index: idx_conversations_status")
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status)"
            ))
            
            logger.info("Creating index: idx_conversations_customer_email")
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_conversations_customer_email ON conversations(customer_email)"
            ))
            
            logger.info("Creating index: idx_conversations_created_at")
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)"
            ))
            
            logger.info("Creating composite index: idx_conversations_escalated_status")
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_conversations_escalated_status ON conversations(escalated, status)"
            ))
            
            logger.info("Creating index: idx_conversations_agent_id")
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_conversations_agent_id ON conversations(agent_id)"
            ))
            
            # Message indexes
            logger.info("Creating index: idx_messages_conversation_id")
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)"
            ))
            
            logger.info("Creating index: idx_messages_timestamp")
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)"
            ))
            
            logger.info("Creating index: idx_messages_sender")
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender)"
            ))
            
            conn.commit()
            logger.info("[SUCCESS] All indexes created successfully!")
            
        except Exception as e:
            logger.error(f"[ERROR] Error creating indexes: {e}")
            conn.rollback()
            raise
    
    engine.dispose()


def analyze_table_stats():
    """Analyze table statistics for query optimization"""
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Get conversation count
        result = conn.execute(text("SELECT COUNT(*) FROM conversations"))
        conv_count = result.fetchone()[0]
        logger.info(f"Total conversations: {conv_count}")
        
        # Get message count
        result = conn.execute(text("SELECT COUNT(*) FROM messages"))
        msg_count = result.fetchone()[0]
        logger.info(f"Total messages: {msg_count}")
        
        # Get escalated conversations
        result = conn.execute(text("SELECT COUNT(*) FROM conversations WHERE escalated = 1"))
        esc_count = result.fetchone()[0]
        logger.info(f"Escalated conversations: {esc_count}")
        
        # Get index list
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"))
        indexes = result.fetchall()
        logger.info(f"\nCurrent indexes ({len(indexes)}):")
        for idx in indexes:
            logger.info(f"  - {idx[0]}")
    
    engine.dispose()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("DATABASE OPTIMIZATION - ADDING PERFORMANCE INDEXES")
    print("="*60 + "\n")
    
    # Analyze current state
    print("[Current Database Stats]:")
    analyze_table_stats()
    
    print("\n[Adding Performance Indexes]...")
    add_performance_indexes()
    
    print("\n[Updated Database Stats]:")
    analyze_table_stats()
    
    print("\n" + "="*60)
    print("[COMPLETE] Database optimization complete!")
    print("="*60)
