import shutil
import time
from collections import deque

from .router import HybridPolymathRouter


def system_snapshot() -> dict:
    snapshot = {"timestamp": time.time()}

    try:
        load_average = __import__("os").getloadavg()
        snapshot["loadavg"] = {
            "1m": load_average[0],
            "5m": load_average[1],
            "15m": load_average[2],
        }
    except (AttributeError, OSError):
        snapshot["loadavg"] = None

    try:
        usage = shutil.disk_usage(".")
        snapshot["storage"] = {
            "total_gb": round(usage.total / 1024**3, 2),
            "free_gb": round(usage.free / 1024**3, 2),
        }
    except OSError:
        snapshot["storage"] = None

    return snapshot


class TelemetryEngine:
    def __init__(self):
        self.router = HybridPolymathRouter()
        self.last_query = "system boot"
        self.afko_status = {"state": "starting"}
        self.history = deque(maxlen=80)

    def update_query(self, query: str):
        self.last_query = query
        self.history.appendleft(
            {"timestamp": time.time(), "type": "query", "value": query}
        )

    def generate(self) -> dict:
        routing = self.router.evaluate(self.last_query)
        snapshot = {
            "timestamp": time.time(),
            "routing_engine": routing["engine"],
            "active_hardware_kernel": routing["active_kernel"],
            "kv_cache_savings": f'{routing["kv_cache_savings_pct"]}%',
            "allocation_justification": routing["reasoning"],
            "hardware": routing["hardware"],
            "afko_status": self.afko_status,
            "system": system_snapshot(),
        }
        self.history.appendleft(
            {"timestamp": snapshot["timestamp"], "type": "telemetry", "value": snapshot}
        )
        return snapshot

    def get_history(self):
        return list(self.history)

    def update_afko_status(self, status: dict):
        self.afko_status = status
        self.history.appendleft(
            {"timestamp": time.time(), "type": "afko_status", "value": status}
        )