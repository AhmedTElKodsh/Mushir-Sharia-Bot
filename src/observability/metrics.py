"""Small Prometheus text-format metrics collector."""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import DefaultDict, Dict


class MetricsRegistry:
    def __init__(self):
        self._lock = Lock()
        self.request_count: DefaultDict[str, int] = defaultdict(int)
        self.error_count: DefaultDict[str, int] = defaultdict(int)
        self.latency_sum: DefaultDict[str, float] = defaultdict(float)

    def record(self, path: str, status_code: int, duration_seconds: float) -> None:
        key = self._label(path)
        with self._lock:
            self.request_count[key] += 1
            self.latency_sum[key] += duration_seconds
            if status_code >= 500:
                self.error_count[key] += 1

    def render(self) -> str:
        lines = [
            "# HELP mushir_request_count Total HTTP requests.",
            "# TYPE mushir_request_count counter",
        ]
        with self._lock:
            for path, value in sorted(self.request_count.items()):
                lines.append(f'mushir_request_count{{path="{path}"}} {value}')
            lines.extend(
                [
                    "# HELP mushir_error_count Total HTTP 5xx responses.",
                    "# TYPE mushir_error_count counter",
                ]
            )
            for path, value in sorted(self.error_count.items()):
                lines.append(f'mushir_error_count{{path="{path}"}} {value}')
            lines.extend(
                [
                    "# HELP mushir_latency_seconds_sum Total HTTP latency by path.",
                    "# TYPE mushir_latency_seconds_sum counter",
                ]
            )
            for path, value in sorted(self.latency_sum.items()):
                lines.append(f'mushir_latency_seconds_sum{{path="{path}"}} {value:.6f}')
        return "\n".join(lines) + "\n"

    @staticmethod
    def timer() -> float:
        return time.perf_counter()

    @staticmethod
    def _label(path: str) -> str:
        return path.replace('"', "")
