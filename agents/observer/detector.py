"""
Z-score anomaly detector.
Keeps a sliding window of metric values per service+metric key.
When a new value deviates beyond the threshold, emits an anomaly.
"""
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from core.config import settings
from core.events import AnomalySeverity


@dataclass
class MetricWindow:
    values: deque = field(default_factory=lambda: deque(maxlen=50))

    def push(self, value: float) -> None:
        self.values.append(value)

    def mean(self) -> float:
        return float(np.mean(self.values))

    def std(self) -> float:
        return float(np.std(self.values)) or 1.0

    def z_score(self, value: float) -> float:
        return (value - self.mean()) / self.std()

    def ready(self) -> bool:
        """Need at least 10 values before we trust the baseline."""
        return len(self.values) >= 10


def severity(z: float) -> AnomalySeverity:
    az = abs(z)
    if az >= 6:
        return AnomalySeverity.CRITICAL
    if az >= 4:
        return AnomalySeverity.HIGH
    if az >= 3:
        return AnomalySeverity.MEDIUM
    return AnomalySeverity.LOW


class AnomalyDetector:
    def __init__(self) -> None:
        self._windows: dict[str, MetricWindow] = {}

    def _key(self, service: str, metric: str) -> str:
        return f"{service}:{metric}"

    def ingest(self, service: str, metric: str, value: float) -> dict | None:
        """
        Push a new value. Returns anomaly dict if detected, else None.
        """
        key = self._key(service, metric)
        if key not in self._windows:
            self._windows[key] = MetricWindow()

        window = self._windows[key]

        if window.ready():
            z = window.z_score(value)
            if abs(z) >= settings.observer_zscore_threshold:
                result = {
                    "service":        service,
                    "metric":         metric,
                    "current_value":  value,
                    "baseline_mean":  window.mean(),
                    "baseline_std":   window.std(),
                    "z_score":        round(z, 3),
                    "severity":       severity(z).value,
                    "window_seconds": settings.observer_window_seconds,
                }
                window.push(value)
                return result

        window.push(value)
        return None
