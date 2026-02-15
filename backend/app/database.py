"""
PostgreSQL Database Configuration
Production-ready database with connection pooling
Maintains SQLite fallback for development
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import logging

logger = logging.getLogger(__name__)

# Get database URL from environment or use SQLite  as fallback
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")

# Determine if using PostgreSQL
IS_POSTGRES = DATABASE_URL.startswith("postgresql")

# Engine configuration
engine_kwargs = {
    "echo": False,  # Set to True for SQL logging
}

if IS_POSTGRES:
    # PostgreSQL production configuration
    engine_kwargs.update({
        "poolclass": QueuePool,
        "pool_size": 20,  # Number of permanent connections
        "max_overflow": 10,  # Additional connections when pool is full
        "pool_timeout": 30,  # Seconds to wait for connection
        "pool_recycle": 3600,  # Recycle connections every hour
        "pool_pre_ping": True,  # Test connections before use
    })
    logger.info("🐘 Using PostgreSQL database (production mode)")
else:
    # SQLite development configuration
    engine_kwargs.update({
        "connect_args": {"check_same_thread": False}
    })
    logger.info("📁 Using SQLite database (development mode)")

# Create engine
engine = create_engine(DATABASE_URL, **engine_kwargs)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base model class
Base = declarative_base()


# Dependency for FastAPI
def get_db():
    """
    Get database session for FastAPI dependency injection
    
    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database health check
def check_database_health() -> dict:
    """
    Check database connection health
    
    Returns:
        dict with status, database_type, and connection info
    """
    try:
        # Try to connect
        connection = engine.connect()
        connection.close()
        
        return {
            "status": "healthy",
            "database_type": "postgresql" if IS_POSTGRES else "sqlite",
            "url": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "local",
            "pool_size": engine.pool.size() if IS_POSTGRES else "N/A",
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "database_type": "postgresql" if IS_POSTGRES else "sqlite",
        }


# Initialize database tables
def init_database():
    """
    Create all database tables
    Should be called on application startup
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
