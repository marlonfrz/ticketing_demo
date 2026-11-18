import hashlib
import ipaddress
import logging
from functools import lru_cache

from fastapi import HTTPException, Request, status
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings


logger = logging.getLogger(__name__)

RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


@lru_cache(maxsize=1)
def _get_redis_client() -> Redis | None:
    if not settings.redis_url:
        return None
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=0.5,
        socket_timeout=0.5,
    )


def _get_client_host(request: Request) -> str:
    if settings.trusted_proxy_headers_enabled:
        forwarded_host = request.headers.get("x-ticketing-client-ip")
        if forwarded_host:
            try:
                return str(ipaddress.ip_address(forwarded_host.strip()))
            except ValueError:
                logger.warning("Ignoring invalid forwarded client IP")

    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, limit: int, window_seconds: int):
    def enforce(request: Request) -> None:
        if not settings.rate_limit_enabled:
            return

        client = _get_redis_client()
        if client is None:
            return

        client_host = _get_client_host(request)
        identity = hashlib.sha256(
            f"{settings.secret_key}:{client_host}".encode("utf-8")
        ).hexdigest()
        key = f"{settings.rate_limit_key_prefix}:{scope}:{identity}"

        try:
            current = int(client.eval(RATE_LIMIT_SCRIPT, 1, key, window_seconds))
        except RedisError as exc:
            logger.warning("Rate limiter unavailable: %s", exc)
            return

        if current > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiadas solicitudes. Inténtalo de nuevo más tarde.",
                headers={"Retry-After": str(window_seconds)},
            )

    return enforce


account_status_rate_limit = rate_limit("auth:account-status", 20, 300)
register_rate_limit = rate_limit("auth:register", 5, 3600)
login_rate_limit = rate_limit("auth:login", 10, 300)
forgot_password_rate_limit = rate_limit("auth:forgot-password", 5, 3600)
reset_password_rate_limit = rate_limit("auth:reset-password", 10, 3600)
contact_rate_limit = rate_limit("contact:organizer", 5, 3600)
reservation_rate_limit = rate_limit("checkout:reservation", 20, 60)
public_relations_register_rate_limit = rate_limit("public-relations:register", 10, 3600)
