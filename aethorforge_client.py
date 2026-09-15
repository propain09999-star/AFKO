import json
import logging
from urllib.error import URLError
from urllib.request import Request, urlopen


class AethorforgeClient:
    def __init__(self, base_url: str, timeout: float = 2.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, payload: dict) -> dict | None:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, ValueError) as exc:
            logging.warning("AETHORFORGE bridge unavailable: %s", exc)
            return None

    def publish_status(self, status: dict) -> dict | None:
        return self._post("/api/status", status)