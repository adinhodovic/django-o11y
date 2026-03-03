"""WebSocket consumers for the test project."""

from channels.generic.websocket import JsonWebsocketConsumer


class EchoConsumer(JsonWebsocketConsumer):
    """Accept any WebSocket connection and echo received JSON messages back."""

    def connect(self) -> None:
        self.accept()

    def disconnect(self, code: int) -> None:
        pass

    def receive_json(self, content: dict, **kwargs) -> None:
        self.send_json({"echo": content})
