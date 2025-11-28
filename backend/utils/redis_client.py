"""Redis client utility for short-term memory and caching"""
import json
import os
from typing import Any, Optional
import redis
import structlog

logger = structlog.get_logger()


class RedisClient:
    """Redis client for caching and short-term memory"""

    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "redis")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.password = os.getenv("REDIS_PASSWORD", None)
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        """Get or create Redis client"""
        if not self._client:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                decode_responses=True
            )
        return self._client

    def set(self, key: str, value: Any, ex: Optional[int] = None):
        """Set key-value pair with optional expiry"""
        try:
            serialized = json.dumps(value) if not isinstance(value, str) else value
            self.client.set(key, serialized, ex=ex)
            logger.debug("redis_set", key=key, ex=ex)
        except Exception as e:
            logger.error("redis_set_error", error=str(e), key=key)
            raise

    def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        try:
            value = self.client.get(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logger.error("redis_get_error", error=str(e), key=key)
            return None

    def delete(self, key: str):
        """Delete key"""
        try:
            self.client.delete(key)
            logger.debug("redis_delete", key=key)
        except Exception as e:
            logger.error("redis_delete_error", error=str(e), key=key)

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return self.client.exists(key) > 0

    def expire(self, key: str, seconds: int):
        """Set expiry on key"""
        self.client.expire(key, seconds)

    def close(self):
        """Close Redis connection"""
        if self._client:
            self._client.close()


# Global Redis client instance
redis_client = RedisClient()
