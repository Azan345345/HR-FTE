"""API quota tracking using in-memory counters (Upstash Redis optional)."""

import structlog
from datetime import datetime
from typing import Dict, Tuple
from app.config import settings
from app.core.llm_router import MODEL_CONFIGS

logger = structlog.get_logger()

# In-memory quota tracking (works without Redis)
_usage: Dict[str, int] = {}  # key → count


def _key(provider: str, model: str, period: str) -> str:
    return f"quota:{provider}:{model}:{period}"


async def get_quota_usage(provider: str, model: str, period: str = "rpd") -> int:
    """Get current usage count for a provider/model/period."""
    k = _key(provider, model, period)
    return _usage.get(k, 0)


async def increment_quota(provider: str, model: str, period: str = "rpd", amount: int = 1):
    """Increment usage counter."""
    k = _key(provider, model, period)
    _usage[k] = _usage.get(k, 0) + amount


async def check_quota_available(model: str) -> Tuple[bool, float]:
    """Check if a model has available quota.

    Returns:
        (is_available, usage_percentage)
    """
    cfg = MODEL_CONFIGS.get(model)
    if not cfg:
        return True, 0.0

    provider = cfg["provider"]
    limit = cfg.get("rpd", 999999)
    used = await get_quota_usage(provider, model, "rpd")
    pct = (used / limit) * 100 if limit > 0 else 0

    if pct >= 100:
        logger.warning("quota_exhausted", model=model, used=used, limit=limit)
        return False, pct

    if pct >= 80:
        logger.warning("quota_warning", model=model, used=used, limit=limit, pct=f"{pct:.1f}%")

    return True, pct


async def get_all_quota_status() -> list[dict]:
    """Get quota status for all configured models."""
    result = []
    for model_id, cfg in MODEL_CONFIGS.items():
        provider = cfg["provider"]
        rpd_limit = cfg.get("rpd", 0)
        used = await get_quota_usage(provider, model_id, "rpd")
        pct = (used / rpd_limit) * 100 if rpd_limit > 0 else 0
        result.append({
            "model": model_id,
            "provider": provider,
            "used": used,
            "limit": rpd_limit,
            "percentage": round(pct, 1),
        })
    return result


async def reset_daily_counters():
    """Reset all daily counters (call at midnight)."""
    keys_to_reset = [k for k in _usage if ":rpd" in k]
    for k in keys_to_reset:
        _usage[k] = 0
    logger.info("daily_quota_reset", keys_reset=len(keys_to_reset))
