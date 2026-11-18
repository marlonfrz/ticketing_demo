from app.api.routes.payments import _resolve_frontend_base_url
from app.core.config import settings


def test_uses_allowed_request_origin_for_checkout_return(monkeypatch):
    monkeypatch.setattr(
        settings,
        "cors_allow_origins",
        "http://localhost:5173,https://frontend.example.com/",
    )
    monkeypatch.setattr(settings, "frontend_base_url", "https://configured.example.com/")

    assert (
        _resolve_frontend_base_url("http://localhost:5173")
        == "http://localhost:5173"
    )
    assert (
        _resolve_frontend_base_url("https://frontend.example.com/")
        == "https://frontend.example.com"
    )


def test_prefers_explicit_allowed_checkout_return_origin(monkeypatch):
    monkeypatch.setattr(
        settings,
        "cors_allow_origins",
        "http://localhost:5173,https://mobile-tunnel.example.com",
    )
    monkeypatch.setattr(settings, "frontend_base_url", "https://configured.example.com")

    assert (
        _resolve_frontend_base_url(
            "https://mobile-tunnel.example.com",
            "http://localhost:5173",
        )
        == "https://mobile-tunnel.example.com"
    )


def test_ignores_untrusted_explicit_origin_and_uses_trusted_request_origin(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "cors_allow_origins", "https://frontend.example.com")
    monkeypatch.setattr(settings, "frontend_base_url", "https://configured.example.com")

    assert (
        _resolve_frontend_base_url(
            "https://attacker.example.com",
            "https://frontend.example.com",
        )
        == "https://frontend.example.com"
    )


def test_uses_private_network_origin_during_local_development(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "cors_allow_origins", "http://localhost:5173")
    monkeypatch.setattr(settings, "frontend_base_url", "http://localhost:5173")

    assert (
        _resolve_frontend_base_url("http://192.168.1.25:5173")
        == "http://192.168.1.25:5173"
    )


def test_rejects_private_network_origin_in_production(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "cors_allow_origins", "https://frontend.example.com")
    monkeypatch.setattr(settings, "frontend_base_url", "https://frontend.example.com")

    assert (
        _resolve_frontend_base_url("http://192.168.1.25:5173")
        == "https://frontend.example.com"
    )


def test_rejects_untrusted_request_origin_for_checkout_return(monkeypatch):
    monkeypatch.setattr(settings, "cors_allow_origins", "http://localhost:5173")
    monkeypatch.setattr(settings, "frontend_base_url", "https://configured.example.com/")

    assert (
        _resolve_frontend_base_url("https://attacker.example.com")
        == "https://configured.example.com"
    )
    assert _resolve_frontend_base_url(None) == "https://configured.example.com"
