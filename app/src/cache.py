import os

import redis

# Connect to Redis
redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=int(os.getenv("REDIS_PORT", 6379)), db=0)
redis_ttl = int(os.getenv("REDIS_TTL", 30))

# API Configuration
API_RATE_LIMIT = 5  # requests per minute
API_RATE_WINDOW = 60  # seconds
REQUEST_TIMEOUT = 30  # seconds


def is_rate_limited() -> bool:
    """Check if we're rate limited by counting requests in Redis."""
    current = redis_client.get("api_request_count")
    if current is None:
        redis_client.setex("api_request_count", API_RATE_WINDOW, 1)
        return False

    count = int(current)
    if count >= API_RATE_LIMIT:
        return True

    redis_client.incr("api_request_count")
    return False
