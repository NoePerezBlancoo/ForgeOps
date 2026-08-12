import hashlib
import threading
import time
from collections.abc import Callable

from fastapi import HTTPException, Request, Response, status
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.redis import get_redis

_fallback_lock = threading.Lock()
_fallback_windows: dict[str, tuple[int, float]] = {}


def _parse_rule(value: str) -> tuple[int, int]:
    try:
        limit, window = (int(part) for part in value.split("/", maxsplit=1))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Regla de rate limiting no valida: {value}") from exc
    if limit < 1 or window < 1:
        raise RuntimeError(f"Regla de rate limiting no valida: {value}")
    return limit, window


def _fallback_hit(key: str, window: int) -> int:
    now = time.monotonic()
    with _fallback_lock:
        count, expires_at = _fallback_windows.get(key, (0, now + window))
        if expires_at <= now:
            count, expires_at = 0, now + window
        count += 1
        _fallback_windows[key] = (count, expires_at)
        if len(_fallback_windows) > 10000:
            expired = [item for item, value in _fallback_windows.items() if value[1] <= now]
            for item in expired:
                _fallback_windows.pop(item, None)
        return count


def rate_limit(scope: str, setting_name: str) -> Callable:
    def dependency(request: Request, response: Response) -> None:
        if not settings.rate_limit_enabled:
            return
        limit, window = _parse_rule(getattr(settings, setting_name))
        identity = request.client.host if request.client else "unknown"
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
        bucket = int(time.time()) // window
        key = f"forgeops:rate:{scope}:{digest}:{bucket}"
        try:
            pipeline = get_redis().pipeline()
            pipeline.incr(key)
            pipeline.expire(key, window + 1)
            count = int(pipeline.execute()[0])
        except RedisError as exc:
            if settings.redis_required or settings.app_env == "production":
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="El control de acceso no esta disponible temporalmente",
                ) from exc
            count = _fallback_hit(key, window)
        remaining = max(0, limit - count)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiadas solicitudes. Espera antes de volver a intentarlo.",
                headers={"Retry-After": str(window)},
            )

    return dependency
