"""
Performance Metrics API Endpoint
Exposes system performance metrics
"""

from fastapi import APIRouter, Depends
from typing import Dict
from app.middleware.performance import get_performance_monitor
from app.utils.cache import get_sentiment_cache
import psutil
import os

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/performance")
async def get_performance_metrics() -> Dict:
    """
    Get current system performance metrics
    
    Returns comprehensive metrics including:
    - Request statistics
    - Response times
    - Error rates
    - Memory usage
    - Cache statistics
    """
    monitor = get_performance_monitor()
    
    if monitor is None:
        return {
            "error": "Performance monitoring not enabled",
            "metrics": None
        }
    
    # Get monitoring metrics
    metrics = monitor.get_metrics()
    
    # Add cache statistics
    cache = get_sentiment_cache()
    metrics['cache'] = cache.get_stats()
    
    return {
        "status": "healthy",
        "metrics": metrics
    }


@router.get("/system")
async def get_system_metrics() -> Dict:
    """Get system resource metrics"""
    process = psutil.Process(os.getpid())
    
    return {
        "cpu_percent": round(process.cpu_percent(interval=0.1), 2),
        "memory": {
            "used_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "percent": round(process.memory_percent(), 2)
        },
        "threads": process.num_threads(),
        "connections": len(process.connections()),
        "open_files": len(process.open_files()),
        "system": {
            "cpu_count": psutil.cpu_count(),
            "total_memory_mb": round(psutil.virtual_memory().total / 1024 / 1024, 2),
            "available_memory_mb": round(psutil.virtual_memory().available / 1024 / 1024, 2)
        }
    }


@router.post("/reset")
async def reset_metrics() -> Dict:
    """Reset performance metrics"""
    monitor = get_performance_monitor()
    
    if monitor is None:
        return {"error": "Performance monitoring not enabled"}
    
    monitor.reset_metrics()
    
    # Also reset cache
    cache = get_sentiment_cache()
    cache.clear()
    
    return {
        "status": "success",
        "message": "All metrics reset"
    }


@router.get("/health")
async def health_check() -> Dict:
    """
    Health check endpoint with detailed status
    
    Returns:
    - Overall system health
    - Performance indicators
    - Service availability
    """
    monitor = get_performance_monitor()
    
    # Determine health status
    health_status = "healthy"
    issues = []
    
    if monitor:
        metrics = monitor.get_metrics()
        
        # Check error rate
        if metrics['error_rate'] > 10:
            health_status = "degraded"
            issues.append(f"High error rate: {metrics['error_rate']}%")
        
        # Check average response time
        if metrics['average_response_time'] > 5:
            health_status = "degraded"
            issues.append(f"Slow response time: {metrics['average_response_time']}s")
        
        # Check memory
        memory_mb = metrics['system_metrics']['memory_mb']
        if memory_mb > 1000:  # 1GB
            health_status = "warning"
            issues.append(f"High memory usage: {memory_mb}MB")
    
    return {
        "status": health_status,
        "timestamp": process().create_time() if 'process' in dir() else None,
        "issues": issues if issues else None,
        "uptime_seconds": round(time.time() - psutil.Process().create_time()) if psutil else None
    }


import time
