"""ASGI configuration for the test project.

Wires Django Channels with ChannelsLoggingMiddleware for local dev WebSocket
observability. Not used by the automated test suite — only loaded when
ASGI_APPLICATION is set (i.e. local.py settings / Docker Compose).
"""
# pylint: disable=wrong-import-position

from django.core.asgi import get_asgi_application

django_http_handler = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

import tests.ws_urls  # noqa: E402
from django_o11y.logging.middleware import ChannelsLoggingMiddleware  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_http_handler,
        # ChannelsLoggingMiddleware sits outside AuthMiddlewareStack so that
        # scope["user"] is already resolved when connection events are logged.
        "websocket": ChannelsLoggingMiddleware(
            AuthMiddlewareStack(URLRouter(tests.ws_urls.websocket_urlpatterns))
        ),
    }
)
