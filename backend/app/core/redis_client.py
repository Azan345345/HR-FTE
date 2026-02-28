"""Redis client initialization for Upstash Redis."""

import structlog
from upstash_redis import Redis
from app.config import settings

logger = structlog.get_logger()

# Initialize Upstash Redis client
redis_client = None

if settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN:
    try:
        redis_client = Redis(
            url=settings.UPSTASH_REDIS_REST_URL,
            token=settings.UPSTASH_REDIS_REST_TOKEN
        )
        logger.info("redis_connected", provider="upstash")
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
else:
    logger.warning("redis_config_missing", detail="Upstash Redis URL or Token not found in settings")

async def update_agent_status(session_id: str, agent_name: str, status: str, progress: int, plan: str = ""):
    """Update agent status in Redis for observability."""
    if not redis_client:
        return

    try:
        # upstash-redis is synchronous by default, but we can wrap it or just call it 
        # since it's a lightweight REST call. For true async we'd use 'redis' package 
        # with async/await if supported by Upstash, but the requirement specifically 
        # mentioned Upstash Redis.
        redis_client.hset(
            f"agent_status:{session_id}",
            mapping={
                "current_agent": agent_name,
                "status": status,
                "progress": str(progress),
                "plan": plan
            }
        )
    except Exception as e:
        logger.error("redis_update_failed", error=str(e))
