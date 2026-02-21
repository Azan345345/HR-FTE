"""
Digital FTE - API Quota Manager (Redis-based)
Tracks RPM/RPD/TPM per provider and warns at 80% usage.
"""

import structlog
from datetime import date

from app.db.redis_client import redis_client

logger = structlog.get_logger()


class QuotaManager:
    """Track and enforce API quota limits using Redis counters."""

    LIMITS = {
        "gemini": {
            "gemini-2.0-flash": {"rpm": 15, "rpd": 1500, "tpm": 1_000_000},
        },
        "groq": {
            "llama-3.3-70b-versatile": {"rpm": 30, "rpd": 14_400, "tpm": 131_072},
            "mixtral-8x7b-32768": {"rpm": 30, "rpd": 14_400, "tpm": 131_072},
            "llama-3.1-8b-instant": {"rpm": 30, "rpd": 14_400, "tpm": 131_072},
        },
        "serpapi": {"default": {"rpd": 100}},
        "hunter": {"default": {"rpd": 25}},
    }

    # ── Keys ─────────────────────────────────────────

    @staticmethod
    def _rpm_key(provider: str, model: str) -> str:
        return f"quota:{provider}:{model}:rpm"

    @staticmethod
    def _rpd_key(provider: str, model: str) -> str:
        return f"quota:{provider}:{model}:rpd:{date.today().isoformat()}"

    @staticmethod
    def _tpm_key(provider: str, model: str) -> str:
        return f"quota:{provider}:{model}:tpm"

    # ── Check ────────────────────────────────────────

    async def can_use(self, provider: str, model: str = "default") -> bool:
        """Return True if we are below 80% of rate limits."""
        limits = self.LIMITS.get(provider, {}).get(model, {})
        if not limits:
            return True

        # Check RPM
        if "rpm" in limits:
            current = int(await redis_client.get(self._rpm_key(provider, model)) or 0)
            if current >= limits["rpm"] * 0.8:
                logger.warning("quota_rpm_high", provider=provider, model=model, current=current)
                return False

        # Check RPD
        if "rpd" in limits:
            current = int(await redis_client.get(self._rpd_key(provider, model)) or 0)
            if current >= limits["rpd"] * 0.8:
                logger.warning("quota_rpd_high", provider=provider, model=model, current=current)
                return False

        return True

    # ── Record ───────────────────────────────────────

    async def record_usage(
        self, provider: str, model: str = "default", tokens: int = 0
    ):
        """Increment counters after a successful API call."""
        pipe = redis_client.pipeline()

        # RPM (expires in 60s)
        rpm_key = self._rpm_key(provider, model)
        pipe.incr(rpm_key)
        pipe.expire(rpm_key, 60)

        # RPD (expires in 24h)
        rpd_key = self._rpd_key(provider, model)
        pipe.incr(rpd_key)
        pipe.expire(rpd_key, 86_400)

        # TPM (expires in 60s)
        if tokens > 0:
            tpm_key = self._tpm_key(provider, model)
            pipe.incrby(tpm_key, tokens)
            pipe.expire(tpm_key, 60)

        await pipe.execute()

    # ── Status ───────────────────────────────────────

    async def get_status(self, provider: str, model: str = "default") -> dict:
        """Return current usage vs limits for a provider/model."""
        limits = self.LIMITS.get(provider, {}).get(model, {})
        rpm = int(await redis_client.get(self._rpm_key(provider, model)) or 0)
        rpd = int(await redis_client.get(self._rpd_key(provider, model)) or 0)
        tpm = int(await redis_client.get(self._tpm_key(provider, model)) or 0)
        return {
            "provider": provider,
            "model": model,
            "rpm": {"used": rpm, "limit": limits.get("rpm")},
            "rpd": {"used": rpd, "limit": limits.get("rpd")},
            "tpm": {"used": tpm, "limit": limits.get("tpm")},
        }


quota_manager = QuotaManager()
