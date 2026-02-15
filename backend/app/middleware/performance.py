"""
Performance Monitoring Middleware
Tracks API response times and system metrics
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import psutil
import os

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddle(BaseHTTPMiddleware):
    """Middleware to monitor API performance metrics"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.request_count = 0
        self.total_time = 0.0
        self.slow_requests = []
        self.error_count = 0
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track request timing and metrics"""
        
        # Start timing
        start_time = time.time()
        self.request_count += 1
        
        # Get process info
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Track errors
            if status_code >= 400:
                self.error_count += 1
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            self.error_count += 1
            raise
        finally:
            # Calculate metrics
            duration = time.time() - start_time
            self.total_time += duration
            
            mem_after = process.memory_info().rss / 1024 / 1024  # MB
            mem_delta = mem_after - mem_before
            
            # Log slow requests (>2 seconds)
            if duration > 2.0:
                slow_request = {
                    'path': request.url.path,
                    'method': request.method,
                    'duration': round(duration, 3),
                    'status': status_code if 'status_code' in locals() else 500
                }
                self.slow_requests.append(slow_request)
                logger.warning(f"⚠️ Slow request: {request.method} {request.url.path} - {duration:.3f}s")
            
            # Log request details
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {status_code if 'status_code' in locals() else 500} - "
                f"Duration: {duration:.3f}s - "
                f"Memory: {mem_after:.1f}MB (Δ{mem_delta:+.2f}MB)"
            )
            
            # Add performance headers
            if 'response' in locals():
                response.headers["X-Request-Duration"] = f"{duration:.3f}"
                response.headers["X-Memory-Usage"] = f"{mem_after:.1f}"
        
        return response
    
    def get_metrics(self) -> dict:
        """Get current performance metrics"""
        avg_time = self.total_time / self.request_count if self.request_count > 0 else 0
        error_rate = self.error_count / self.request_count if self.request_count > 0 else 0
        
        process = psutil.Process(os.getpid())
        
        return {
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate': round(error_rate * 100, 2),
            'average_response_time': round(avg_time, 3),
            'total_processing_time': round(self.total_time, 2),
            'slow_requests_count': len(self.slow_requests),
            'recent_slow_requests': self.slow_requests[-10:],  # Last 10
            'system_metrics': {
                'cpu_percent': process.cpu_percent(),
                'memory_mb': round(process.memory_info().rss / 1024 / 1024, 1),
                'threads': process.num_threads(),
                'open_files': len(process.open_files())
            }
        }
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.request_count = 0
        self.total_time = 0.0
        self.slow_requests = []
        self.error_count = 0


# Global instance
performance_monitor = None


def get_performance_monitor():
    """Get the global performance monitor instance"""
    global performance_monitor
    return performance_monitor


def set_performance_monitor(monitor: PerformanceMonitoringMiddle):
    """Set the global performance monitor instance"""
    global performance_monitor
    performance_monitor = monitor
