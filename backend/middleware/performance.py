"""
Performance Monitoring Middleware
Fase 1: Instrumentación de rendimiento para diagnóstico
- Métricas p50/p95/p99 por endpoint
- Log de queries lentas
- Tamaño de payloads
"""
import time
import asyncio
import statistics
import logging
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import json

logger = logging.getLogger("performance")
logger.setLevel(logging.INFO)

# ==================== METRICS STORAGE ====================
class PerformanceMetrics:
    """In-memory storage for performance metrics (últimas 1000 requests por endpoint)"""
    
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._latencies: Dict[str, List[float]] = defaultdict(list)
        self._payload_sizes: Dict[str, List[int]] = defaultdict(list)
        self._slow_queries: List[dict] = []
        self._request_count: Dict[str, int] = defaultdict(int)
        self._error_count: Dict[str, int] = defaultdict(int)
        
    def record_request(self, endpoint: str, method: str, latency_ms: float, 
                       payload_size: int, status_code: int):
        """Record a request's performance data"""
        key = f"{method}:{endpoint}"
        
        # Latency
        self._latencies[key].append(latency_ms)
        if len(self._latencies[key]) > self.max_samples:
            self._latencies[key] = self._latencies[key][-self.max_samples:]
        
        # Payload size
        self._payload_sizes[key].append(payload_size)
        if len(self._payload_sizes[key]) > self.max_samples:
            self._payload_sizes[key] = self._payload_sizes[key][-self.max_samples:]
        
        # Counters
        self._request_count[key] += 1
        if status_code >= 400:
            self._error_count[key] += 1
        
        # Log slow requests (>500ms)
        if latency_ms > 500:
            self._slow_queries.append({
                "endpoint": key,
                "latency_ms": round(latency_ms, 2),
                "payload_bytes": payload_size,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": status_code
            })
            if len(self._slow_queries) > 500:
                self._slow_queries = self._slow_queries[-500:]
    
    def get_percentiles(self, key: str) -> dict:
        """Calculate p50, p95, p99 for an endpoint"""
        latencies = self._latencies.get(key, [])
        if not latencies:
            return {"p50": 0, "p95": 0, "p99": 0, "avg": 0, "count": 0}
        
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        return {
            "p50": round(sorted_lat[int(n * 0.50)] if n > 0 else 0, 2),
            "p95": round(sorted_lat[int(n * 0.95)] if n >= 20 else sorted_lat[-1], 2),
            "p99": round(sorted_lat[int(n * 0.99)] if n >= 100 else sorted_lat[-1], 2),
            "avg": round(statistics.mean(latencies), 2),
            "min": round(min(latencies), 2),
            "max": round(max(latencies), 2),
            "count": n
        }
    
    def get_payload_stats(self, key: str) -> dict:
        """Get payload size statistics"""
        sizes = self._payload_sizes.get(key, [])
        if not sizes:
            return {"avg_kb": 0, "max_kb": 0}
        return {
            "avg_kb": round(statistics.mean(sizes) / 1024, 2),
            "max_kb": round(max(sizes) / 1024, 2)
        }
    
    def get_top_slow_endpoints(self, n: int = 10) -> List[dict]:
        """Get top N slowest endpoints by p95 latency"""
        results = []
        for key in self._latencies.keys():
            stats = self.get_percentiles(key)
            payload = self.get_payload_stats(key)
            results.append({
                "endpoint": key,
                "requests": self._request_count.get(key, 0),
                "errors": self._error_count.get(key, 0),
                **stats,
                **payload
            })
        
        # Sort by p95 descending
        results.sort(key=lambda x: x["p95"], reverse=True)
        return results[:n]
    
    def get_slow_queries_log(self, n: int = 50) -> List[dict]:
        """Get recent slow queries (>500ms)"""
        return self._slow_queries[-n:]
    
    def get_full_report(self) -> dict:
        """Generate full performance report"""
        top_slow = self.get_top_slow_endpoints(20)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "top_20_slowest_endpoints": top_slow,
            "recent_slow_requests": self.get_slow_queries_log(50),
            "summary": {
                "total_endpoints_tracked": len(self._latencies),
                "total_requests": sum(self._request_count.values()),
                "total_errors": sum(self._error_count.values()),
                "endpoints_over_500ms_p95": len([e for e in top_slow if e["p95"] > 500]),
                "endpoints_over_1s_p95": len([e for e in top_slow if e["p95"] > 1000]),
            }
        }

# Global metrics instance
metrics = PerformanceMetrics()

# ==================== MIDDLEWARE ====================
class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track request performance"""
    
    # Endpoints to skip (health checks, static files)
    SKIP_PATHS = {"/health", "/metrics", "/favicon.ico", "/_next"}
    
    async def dispatch(self, request: Request, call_next):
        # Skip certain paths
        path = request.url.path
        if any(skip in path for skip in self.SKIP_PATHS):
            return await call_next(request)
        
        # Normalize path (remove IDs for grouping)
        normalized_path = self._normalize_path(path)
        
        # Start timing
        start_time = time.perf_counter()
        
        # Process request
        response = await call_next(request)
        
        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Get response size (approximate from content-length header)
        content_length = response.headers.get("content-length", "0")
        try:
            payload_size = int(content_length)
        except ValueError:
            payload_size = 0
        
        # Record metrics
        metrics.record_request(
            endpoint=normalized_path,
            method=request.method,
            latency_ms=latency_ms,
            payload_size=payload_size,
            status_code=response.status_code
        )
        
        # Add timing header for debugging
        response.headers["X-Response-Time-Ms"] = str(round(latency_ms, 2))
        
        # Log slow requests
        if latency_ms > 1000:
            logger.warning(
                f"SLOW REQUEST: {request.method} {path} - {latency_ms:.0f}ms - {payload_size/1024:.1f}KB"
            )
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path by replacing UUIDs and IDs with placeholders"""
        import re
        # Replace UUIDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{id}',
            path,
            flags=re.IGNORECASE
        )
        # Replace OT numbers like OT-20260301-XXXXXXXX
        path = re.sub(r'OT-\d{8}-[A-F0-9]+', '{ot_id}', path, flags=re.IGNORECASE)
        # Replace numeric IDs in path segments
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        return path


# ==================== DB QUERY PROFILER ====================
class QueryProfiler:
    """Profile MongoDB queries for slow query detection"""
    
    def __init__(self):
        self._slow_queries: List[dict] = []
        self._query_stats: Dict[str, List[float]] = defaultdict(list)
    
    async def profile_query(self, collection: str, operation: str, query: dict, 
                           duration_ms: float):
        """Record a query execution"""
        key = f"{collection}.{operation}"
        self._query_stats[key].append(duration_ms)
        
        # Log slow queries (>100ms)
        if duration_ms > 100:
            self._slow_queries.append({
                "collection": collection,
                "operation": operation,
                "query": str(query)[:500],  # Truncate long queries
                "duration_ms": round(duration_ms, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            if len(self._slow_queries) > 200:
                self._slow_queries = self._slow_queries[-200:]
            
            logger.warning(f"SLOW QUERY: {key} - {duration_ms:.0f}ms - {str(query)[:200]}")
    
    def get_slow_queries(self, n: int = 50) -> List[dict]:
        return self._slow_queries[-n:]
    
    def get_query_stats(self) -> List[dict]:
        results = []
        for key, times in self._query_stats.items():
            if len(times) >= 5:
                sorted_times = sorted(times)
                n = len(sorted_times)
                results.append({
                    "operation": key,
                    "count": n,
                    "avg_ms": round(statistics.mean(times), 2),
                    "p95_ms": round(sorted_times[int(n * 0.95)], 2) if n >= 20 else round(max(times), 2),
                    "max_ms": round(max(times), 2)
                })
        results.sort(key=lambda x: x["p95_ms"], reverse=True)
        return results[:20]

query_profiler = QueryProfiler()


# ==================== HELPER FOR WRAPPING DB CALLS ====================
async def profile_db_call(collection: str, operation: str, query: dict, coro):
    """Wrapper to profile database calls"""
    start = time.perf_counter()
    try:
        result = await coro
        return result
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        await query_profiler.profile_query(collection, operation, query, duration_ms)
