import redis
from app.core.config import settings

# Redis client configured with decode_responses=True to read JSON payloads directly as strings
redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=3,
)


def check_redis_health() -> bool:
    """Checks Redis server availability via the PING command."""
    try:
        return bool(redis_client.ping())
    except Exception:
        return False