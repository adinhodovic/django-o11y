"""WebSocket URL routing for the test project."""

from django.urls import re_path

from tests.consumers import EchoConsumer

websocket_urlpatterns = [
    re_path(r"ws/echo/$", EchoConsumer.as_asgi()),
]
