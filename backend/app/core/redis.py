from functools import lru_cache

from redis import Redis

from app.core.config import settings


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=settings.redis_socket_timeout_seconds,
        socket_timeout=settings.redis_socket_timeout_seconds,
        health_check_interval=30,
    )


@lru_cache
def get_queue_redis() -> Redis:
    return Redis.from_url(
        settings.redis_url,
        decode_responses=False,
        socket_connect_timeout=settings.redis_socket_timeout_seconds,
        socket_timeout=settings.redis_socket_timeout_seconds,
        health_check_interval=30,
    )


def redis_ready() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:
        return False
