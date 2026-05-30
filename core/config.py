from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model:    str = "mistral:7b"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    topic_metrics:   str = "corvus.metrics"
    topic_anomaly:   str = "corvus.anomaly"
    topic_diagnosis: str = "corvus.diagnosis"
    topic_plan:      str = "corvus.plan"
    topic_action:    str = "corvus.action"
    topic_result:    str = "corvus.result"

    # Postgres
    database_url: str = "postgresql+asyncpg://corvus:corvus@localhost:5432/corvus"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Observer
    observer_window_seconds:   int   = 60
    observer_zscore_threshold: float = 2.5
    observer_emit_sla_ms:      int   = 500

    # Forensics
    forensics_log_window_seconds: int   = 120
    forensics_min_confidence:     float = 0.5

    # Planner
    planner_max_plans:              int   = 3
    planner_auto_approve_threshold: float = 0.3

    # Executor
    executor_step_timeout_seconds: int = 30

    # Gateway
    gateway_port: str = "8000"
    cors_origins:  str = "http://localhost:5173"

    # General
    env:       str = "development"
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_dev(self) -> bool:
        return self.env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
