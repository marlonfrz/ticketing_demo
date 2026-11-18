from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError

from app.core import rate_limit as rate_limit_module
from app.core.config import settings


class FakeRedis:
    def __init__(self, values):
        self.values = iter(values)

    def eval(self, *_args):
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        return value


def test_rate_limit_uses_validated_client_ip_from_trusted_proxy(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "staging")
    request = SimpleNamespace(
        client=SimpleNamespace(host="10.0.0.8"),
        headers={"x-ticketing-client-ip": "203.0.113.25"},
    )

    assert rate_limit_module._get_client_host(request) == "203.0.113.25"


def test_rate_limit_ignores_invalid_forwarded_client_ip(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "staging")
    request = SimpleNamespace(
        client=SimpleNamespace(host="10.0.0.8"),
        headers={"x-ticketing-client-ip": "not-an-ip"},
    )

    assert rate_limit_module._get_client_host(request) == "10.0.0.8"


def test_rate_limit_rejects_requests_over_limit(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    redis_client = FakeRedis([1, 2])
    monkeypatch.setattr(rate_limit_module, "_get_redis_client", lambda: redis_client)
    request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.10"))
    enforce = rate_limit_module.rate_limit("test", 1, 60)

    enforce(request)
    with pytest.raises(HTTPException) as exc_info:
        enforce(request)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {"Retry-After": "60"}


def test_rate_limit_fails_open_when_redis_is_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(
        rate_limit_module,
        "_get_redis_client",
        lambda: FakeRedis([ConnectionError("unavailable")]),
    )
    request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.11"))

    rate_limit_module.rate_limit("test", 1, 60)(request)
