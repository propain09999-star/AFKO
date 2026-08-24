import hmac
import os


class APIKeyMiddleware:
    def __init__(self, app, env_var):
        self.app = app
        self.env_var = env_var

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        expected_key = os.environ.get(self.env_var)
        request_key = next(
            (
                value.decode("latin-1")
                for name, value in scope.get("headers", [])
                if name.lower() == b"x-api-key"
            ),
            None,
        )

        if expected_key is None:
            await self._respond(send, 503, b"service authentication is not configured")
            return
        if request_key is None or not hmac.compare_digest(request_key, expected_key):
            await self._respond(send, 401, b"unauthorized")
            return

        await self.app(scope, receive, send)

    async def _respond(self, send, status, body):
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"text/plain; charset=utf-8"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
