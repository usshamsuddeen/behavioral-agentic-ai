"""
Production Logging Middleware
Comprehensive request/response logging with performance tracking
"""

import time
import logging
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

# Configure logger
logger = logging.getLogger("app.requests")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request/response logging
    Tracks request timing, errors, and provides audit trail
    """
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> StarletteResponse:
        """Process request and log details"""
        
        # Start timing
        start_time = time.time()
        
        # Get request details
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        
        # Log incoming request
        logger.info(f"→ {method} {path} from {client_ip}")
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            status = response.status_code
            status_emoji = "✅" if status < 400 else "⚠️" if status < 500 else "❌"
            
            logger.info(
                f"{status_emoji} {method} {path} → {status} "
                f"({duration*1000:.2f}ms)"
            )
            
            # Add custom headers
            response.headers["X-Response-Time"] = f"{duration*1000:.2f}ms"
            response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "none")
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                f"❌ {method} {path} → ERROR: {str(e)} "
                f"({duration*1000:.2f}ms)",
                exc_info=True
            )
            raise


class APICallLogger:
    """Log API calls to specific endpoints with detailed context"""
    
    @staticmethod
    def log_sentiment_analysis(text: str, result: dict, duration: float):
        """Log sentiment analysis API call"""
        logger.info(
            f"🧠 Sentiment Analysis: "
            f"lang={result.get('language', 'unknown')} "
            f"sentiment={result.get('sentiment')} "
            f"score={result.get('score', 0):.2f} "
            f"model={result.get('model')} "
            f"({duration*1000:.2f}ms)"
        )
    
    @staticmethod
    def log_escalation_check(triggered: bool, score: float, reasons: list):
        """Log escalation check"""
        emoji = "🚨" if triggered else "✓"
        logger.info(
            f"{emoji} Escalation Check: "
            f"triggered={triggered} score={score:.2f} "
            f"reasons={', '.join(reasons[:2]) if reasons else 'none'}"
        )
    
    @staticmethod
    def log_message_sent(conversation_id: str, sender: str, length: int):
        """Log message creation"""
        logger.info(
            f"💬 Message: conv={conversation_id} "
            f"sender={sender} length={length}"
        )
    
    @staticmethod
    def log_conversation_created(conversation_id: str, customer_name: str):
        """Log new conversation"""
        logger.info(
            f"🆕 Conversation Created: id={conversation_id} "
            f"customer={customer_name}"
        )
    
    @staticmethod
    def log_auto_escalation(conversation_id: str, reason: str):
        """Log automatic escalation"""
        logger.warning(
            f"🚨🚨 AUTO-ESCALATION: conv={conversation_id} "
            f"reason='{reason}'"
        )


class ErrorLogger:
    """Centralized error logging"""
    
    @staticmethod
    def log_database_error(operation: str, error: Exception):
        """Log database errors"""
        logger.error(
            f"💾❌ Database Error [{operation}]: {str(error)}",
            exc_info=True
        )
    
    @staticmethod
    def log_nlp_error(model: str, error: Exception):
        """Log NLP model errors"""
        logger.error(
            f"🤖❌ NLP Error [{model}]: {str(error)}",
            exc_info=True
        )
    
    @staticmethod
    def log_cache_error(operation: str, error: Exception):
        """Log cache errors"""
        logger.warning(
            f"🗄️⚠️ Cache Error [{operation}]: {str(error)}"
        )
    
    @staticmethod
    def log_validation_error(field: str, value: any, error: str):
        """Log validation errors"""
        logger.warning(
            f"⚠️ Validation Error: field={field} "
            f"value={value} error={error}"
        )


def configure_logging(level: str = "INFO", log_file: str = None):
    """
    Configure application-wide logging
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for logs
    """
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    logging.getLogger("uvicorn.access").handlers = []  # Disable uvicorn access logs
    logging.getLogger("app").setLevel(level)
    
    logger.info("✅ Logging configured successfully")


# Export commonly used loggers
api_logger = APICallLogger()
error_logger = ErrorLogger()
