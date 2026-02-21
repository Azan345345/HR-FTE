"""
Digital FTE - Quota Manager
Tracks LLM and API usage per user to prevent abuse and manage free-tier limits.
Backed by Redis.
"""
from uuid import UUID
import json
from typing import Dict, Any

from app.core.redis import get_redis_client
from app.core.config import settings

# Example static limits for free tier
DEFAULT_MONTHLY_LLM_REQUESTS = 500
DEFAULT_MONTHLY_JOB_SEARCHES = 100
DEFAULT_MONTHLY_CV_PARSES = 50

class QuotaManager:
    """Manages usage quotas for different operations."""

    def __init__(self):
        self._redis = None

    async def _get_redis(self):
        if not self._redis:
            try:
                self._redis = await get_redis_client()
            except Exception:
                # Fallback to local memory if Redis is unavailable
                self._redis = "MEMORY"
        return self._redis

    def _get_key(self, user_id: UUID, resource: str, period: str = "monthly") -> str:
        """Generate a Redis key for a specific user and resource."""
        # For simplicity, we just use a static period prefix, but this could incorporate year/month
        return f"quota:{user_id}:{period}:{resource}"

    async def get_usage(self, user_id: UUID) -> Dict[str, Any]:
        """Get current usage across all tracked resources."""
        redis = await self._get_redis()
        
        resources = {
            "llm_requests": DEFAULT_MONTHLY_LLM_REQUESTS,
            "job_searches": DEFAULT_MONTHLY_JOB_SEARCHES,
            "cv_parses": DEFAULT_MONTHLY_CV_PARSES
        }
        
        usage_stats = {}
        for resource, limit in resources.items():
            used = 0
            if redis == "MEMORY":
                # Basic in-memory placeholder
                used = 0 
            else:
                key = self._get_key(user_id, resource)
                val = await redis.get(key)
                used = int(val) if val else 0
            
            percentage = (used / limit * 100) if limit > 0 else 0
            
            usage_stats[resource] = {
                "used": used,
                "limit": limit,
                "percentage": round(percentage, 2),
                "is_near_limit": percentage >= 80.0,
                "is_exhausted": used >= limit
            }
            
        return usage_stats

    async def increment_usage(self, user_id: UUID, resource: str, amount: int = 1) -> bool:
        """Increment usage for a resource. Returns False if limit exceeded."""
        redis = await self._get_redis()
        if redis == "MEMORY":
            return True # Allow everything in memory-fallback mode

        key = self._get_key(user_id, resource)
        
        # Define limits
        limits = {
            "llm_requests": DEFAULT_MONTHLY_LLM_REQUESTS,
            "job_searches": DEFAULT_MONTHLY_JOB_SEARCHES,
            "cv_parses": DEFAULT_MONTHLY_CV_PARSES
        }
        
        limit = limits.get(resource, 0)
        
        if limit > 0:
            current = await redis.get(key)
            current_val = int(current) if current else 0
            
            if current_val + amount > limit:
                return False # Limit exceeded
                
        # Increment and set expiry (e.g., 30 days = 2592000 seconds)
        await redis.incrby(key, amount)
        await redis.expire(key, 2592000)
        
        return True

    async def check_quota(self, user_id: UUID, resource: str) -> bool:
        """Check if a user has sufficient quota for a resource."""
        redis = await self._get_redis()
        key = self._get_key(user_id, resource)
        
        limits = {
            "llm_requests": DEFAULT_MONTHLY_LLM_REQUESTS,
            "job_searches": DEFAULT_MONTHLY_JOB_SEARCHES,
            "cv_parses": DEFAULT_MONTHLY_CV_PARSES
        }
        
        limit = limits.get(resource, 0)
        
        if limit == 0:
            return True # No limit defined
            
        current = await redis.get(key)
        current_val = int(current) if current else 0
        
        return current_val < limit

quota_manager = QuotaManager()
