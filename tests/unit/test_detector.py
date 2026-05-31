"""
Unit tests for the Z-score anomaly detector.
No Kafka, no network — pure logic.
"""
import pytest
from agents.observer.detector import AnomalyDetector, severity
from core.events import AnomalySeverity


class TestAnomalyDetector:
    def setup_method(self):
        self.detector = AnomalyDetector()

    def _warm_up(self, service="order-service", metric="cpu_percent", value=40.0, n=15):
        """Push enough normal values to establish a baseline."""
        for _ in range(n):
            self.detector.ingest(service, metric, value)

    def test_no_anomaly_during_warmup(self):
        for i in range(9):
            result = self.detector.ingest("order-service", "cpu_percent", 40.0)
            assert result is None

    def test_no_anomaly_on_normal_value(self):
        self._warm_up()
        result = self.detector.ingest("order-service", "cpu_percent", 42.0)
        assert result is None

    def test_detects_spike(self):
        self._warm_up(value=40.0)
        result = self.detector.ingest("order-service", "cpu_percent", 95.0)
        assert result is not None
        assert result["service"] == "order-service"
        assert result["metric"] == "cpu_percent"
        assert result["z_score"] > 2.5

    def test_anomaly_has_required_fields(self):
        self._warm_up(value=40.0)
        result = self.detector.ingest("order-service", "cpu_percent", 95.0)
        assert result is not None
        for field in ["service", "metric", "current_value",
                      "baseline_mean", "baseline_std", "z_score",
                      "severity", "window_seconds"]:
            assert field in result

    def test_different_services_isolated(self):
        self._warm_up(service="auth-service", metric="cpu_percent", value=40.0)
        # order-service has no baseline yet — should not detect
        result = self.detector.ingest("order-service", "cpu_percent", 95.0)
        assert result is None

    def test_different_metrics_isolated(self):
        self._warm_up(service="order-service", metric="cpu_percent", value=40.0)
        # latency_p99_ms has no baseline yet
        result = self.detector.ingest("order-service", "latency_p99_ms", 9999.0)
        assert result is None


class TestSeverity:
    def test_critical(self):
        assert severity(6.5) == AnomalySeverity.CRITICAL

    def test_high(self):
        assert severity(4.5) == AnomalySeverity.HIGH

    def test_medium(self):
        assert severity(3.2) == AnomalySeverity.MEDIUM

    def test_low(self):
        assert severity(2.6) == AnomalySeverity.LOW

    def test_negative_z_score(self):
        assert severity(-6.5) == AnomalySeverity.CRITICAL
