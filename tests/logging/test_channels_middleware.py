"""Tests for ChannelsLoggingMiddleware."""

import asyncio
import logging
import re
import uuid
from unittest.mock import MagicMock, patch

import pytest
import structlog

from django_o11y.logging.middleware import ChannelsLoggingMiddleware

channels = pytest.importorskip("channels")


def _make_scope(type="websocket", path="/ws/echo/", headers=None, user=None):
    scope = {"type": type, "path": path, "headers": headers or []}
    if user is not None:
        scope["user"] = user
    return scope


async def _noop_inner(scope, receive, send):
    pass


def _log_text(caplog) -> str:
    return " ".join(r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# Pass-through for non-websocket scopes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scope_type", ["http", "lifespan"])
def test_non_websocket_scope_passes_through(scope_type):
    called = []

    async def inner(scope, receive, send):
        called.append(scope["type"])

    middleware = ChannelsLoggingMiddleware(inner)
    asyncio.run(middleware(_make_scope(type=scope_type), None, None))
    assert called == [scope_type]


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def test_websocket_connected_and_disconnected_logged(caplog):
    structlog.contextvars.clear_contextvars()
    middleware = ChannelsLoggingMiddleware(_noop_inner)

    with caplog.at_level(logging.INFO, logger="django_o11y"):
        asyncio.run(middleware(_make_scope(), None, None))

    text = _log_text(caplog)
    assert "websocket_connected" in text
    assert "websocket_disconnected" in text


def test_duration_ms_in_disconnected_log(caplog):
    structlog.contextvars.clear_contextvars()
    middleware = ChannelsLoggingMiddleware(_noop_inner)

    with caplog.at_level(logging.INFO, logger="django_o11y"):
        asyncio.run(middleware(_make_scope(), None, None))

    assert "duration_ms" in _log_text(caplog)


# ---------------------------------------------------------------------------
# request_id
# ---------------------------------------------------------------------------


def test_request_id_propagated_from_header(caplog):
    structlog.contextvars.clear_contextvars()
    headers = [(b"x-request-id", b"test-req-abc")]
    middleware = ChannelsLoggingMiddleware(_noop_inner)

    with caplog.at_level(logging.INFO, logger="django_o11y"):
        asyncio.run(middleware(_make_scope(headers=headers), None, None))

    assert "test-req-abc" in _log_text(caplog)


def test_request_id_generated_when_no_header(caplog):
    structlog.contextvars.clear_contextvars()
    middleware = ChannelsLoggingMiddleware(_noop_inner)

    with caplog.at_level(logging.INFO, logger="django_o11y"):
        asyncio.run(middleware(_make_scope(), None, None))

    uuids = re.findall(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        _log_text(caplog),
    )
    assert len(uuids) >= 1
    uuid.UUID(uuids[0])  # raises if not valid


# ---------------------------------------------------------------------------
# user_id extraction
# ---------------------------------------------------------------------------


def _make_resolved_user(pk=42, username="alice", is_authenticated=True):
    user = MagicMock()
    user.pk = pk
    user.username = username
    user.is_authenticated = is_authenticated
    lazy = MagicMock()
    lazy._wrapped = user
    return lazy


def test_user_id_in_log_for_authenticated_user(caplog):
    structlog.contextvars.clear_contextvars()
    user = _make_resolved_user(pk=7)
    middleware = ChannelsLoggingMiddleware(_noop_inner)

    with caplog.at_level(logging.INFO, logger="django_o11y"):
        asyncio.run(middleware(_make_scope(user=user), None, None))

    assert "7" in _log_text(caplog)


def _make_user_with_empty_sentinel():
    from django.utils.functional import empty

    lazy = MagicMock()
    lazy._wrapped = empty
    return lazy


@pytest.mark.parametrize(
    "make_user",
    [
        # Unresolved LazyObject (None)
        lambda: _make_user_with_wrapped(None),
        # Unresolved LazyObject (django empty sentinel)
        lambda: _make_user_with_empty_sentinel(),
        # Anonymous user
        lambda: _make_anon_user(),
    ],
    ids=["unresolved_lazy_none", "unresolved_lazy_empty", "anonymous"],
)
def test_no_user_id_in_log(make_user, caplog):
    structlog.contextvars.clear_contextvars()
    middleware = ChannelsLoggingMiddleware(_noop_inner)

    with caplog.at_level(logging.INFO, logger="django_o11y"):
        asyncio.run(middleware(_make_scope(user=make_user()), None, None))

    assert "user_id" not in _log_text(caplog)


def _make_user_with_wrapped(wrapped_value):
    lazy = MagicMock()
    lazy._wrapped = wrapped_value
    return lazy


def _make_anon_user():
    anon = MagicMock()
    anon._wrapped = anon
    anon.is_authenticated = False
    return anon


def test_callable_is_authenticated_returns_user_id(caplog):
    """_extract_user_id handles is_authenticated as a callable (old-style Django)."""
    structlog.contextvars.clear_contextvars()

    user = MagicMock()
    user.pk = 99
    user.is_authenticated = lambda: True
    lazy = MagicMock()
    lazy._wrapped = user
    middleware = ChannelsLoggingMiddleware(_noop_inner)

    with caplog.at_level(logging.INFO, logger="django_o11y"):
        asyncio.run(middleware(_make_scope(user=lazy), None, None))

    assert "99" in _log_text(caplog)


def test_callable_is_authenticated_raises_no_user_id(caplog):
    """_extract_user_id swallows exceptions from callable is_authenticated."""
    structlog.contextvars.clear_contextvars()

    user = MagicMock()
    user.pk = 55

    def broken_auth():
        raise RuntimeError("auth error")

    user.is_authenticated = broken_auth
    lazy = MagicMock()
    lazy._wrapped = user
    middleware = ChannelsLoggingMiddleware(_noop_inner)

    with caplog.at_level(logging.INFO, logger="django_o11y"):
        asyncio.run(middleware(_make_scope(user=lazy), None, None))

    assert "user_id" not in _log_text(caplog)


def test_no_user_in_scope_no_crash(caplog):
    structlog.contextvars.clear_contextvars()
    middleware = ChannelsLoggingMiddleware(_noop_inner)

    with caplog.at_level(logging.INFO, logger="django_o11y"):
        asyncio.run(middleware(_make_scope(), None, None))

    assert "websocket_connected" in _log_text(caplog)


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------


def test_exception_logs_error_and_disconnected(caplog):
    structlog.contextvars.clear_contextvars()

    async def broken_inner(scope, receive, send):
        raise RuntimeError("ws boom")

    middleware = ChannelsLoggingMiddleware(broken_inner)

    async def run():
        with pytest.raises(RuntimeError):
            await middleware(_make_scope(), None, None)

    with caplog.at_level(logging.INFO, logger="django_o11y"):
        asyncio.run(run())

    text = _log_text(caplog)
    assert "websocket_error" in text
    assert "ws boom" in text
    assert "websocket_disconnected" not in text


# ---------------------------------------------------------------------------
# Context isolation
# ---------------------------------------------------------------------------


def test_structlog_context_cleared_after_connection():
    structlog.contextvars.clear_contextvars()
    middleware = ChannelsLoggingMiddleware(_noop_inner)

    asyncio.run(middleware(_make_scope(), None, None))

    ctx = structlog.contextvars.get_merged_contextvars(structlog.get_logger())
    assert "request_id" not in ctx
    assert "user_id" not in ctx


def test_structlog_context_cleared_even_after_exception():
    structlog.contextvars.clear_contextvars()

    async def broken_inner(scope, receive, send):
        raise RuntimeError("ws boom")

    middleware = ChannelsLoggingMiddleware(broken_inner)

    async def run():
        with pytest.raises(RuntimeError):
            await middleware(_make_scope(), None, None)

    asyncio.run(run())

    ctx = structlog.contextvars.get_merged_contextvars(structlog.get_logger())
    assert "request_id" not in ctx


# ---------------------------------------------------------------------------
# Import guard
# ---------------------------------------------------------------------------


def test_import_error_without_channels():
    import sys

    import django_o11y.logging.middleware as mod

    original_init = mod.ChannelsLoggingMiddleware.__init__

    def patched_init(self, inner):
        try:
            import channels  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "ChannelsLoggingMiddleware requires 'channels'. "
                "Install it with: pip install django-o11y[channels]"
            ) from exc

    mod.ChannelsLoggingMiddleware.__init__ = patched_init
    try:
        with patch.dict(sys.modules, {"channels": None}):
            with pytest.raises(
                ImportError, match="pip install django-o11y\\[channels\\]"
            ):
                mod.ChannelsLoggingMiddleware(_noop_inner)
    finally:
        mod.ChannelsLoggingMiddleware.__init__ = original_init
