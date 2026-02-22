"""
Global Configuration Settings for Compliance Engine
All URLs, credentials, and system settings are defined here.
Pydantic v2 compatible.
"""

from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache


class DatabaseSettings(BaseSettings):
    """FalkorDB Database Configuration"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    host: str = Field(default="localhost", validation_alias="FALKORDB_HOST")
    port: int = Field(default=6379, validation_alias="FALKORDB_PORT")
    password: Optional[str] = Field(default=None, validation_alias="FALKORDB_PASSWORD")
    rules_graph_name: str = Field(default="RulesGraph", validation_alias="RULES_GRAPH_NAME")
    data_graph_name: str = Field(default="DataTransferGraph", validation_alias="DATA_GRAPH_NAME")
    temp_graph_prefix: str = Field(default="TempGraph_", validation_alias="TEMP_GRAPH_PREFIX")


class AIServiceSettings(BaseSettings):
    """AI/LLM Service Configuration"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Token Generation API
    token_api_url: str = Field(
        default="https://cmb-ib2b-dsp-sjdf/ib2b_tokenTranslator?_action=translate",
        validation_alias="AI_TOKEN_API_URL"
    )
    token_username: str = Field(default="", validation_alias="AI_TOKEN_USERNAME")
    token_password: str = Field(default="", validation_alias="AI_TOKEN_PASSWORD")

    # LLM API
    llm_api_url: str = Field(
        default="https://gapi-api.com/v1/api/v1/chat/completions",
        validation_alias="AI_LLM_API_URL"
    )
    llm_model: str = Field(default="o3-mini", validation_alias="AI_LLM_MODEL")
    llm_use_case_id: str = Field(default="compliance-engine", validation_alias="AI_USE_CASE_ID")

    # Token settings
    token_expiry_buffer_seconds: int = Field(default=300, validation_alias="AI_TOKEN_EXPIRY_BUFFER")

    # AI Feature Flags
    enable_ai_rule_generation: bool = Field(default=True, validation_alias="ENABLE_AI_RULE_GENERATION")
    enable_ai_rule_testing: bool = Field(default=True, validation_alias="ENABLE_AI_RULE_TESTING")

    # Agentic Mode - enables autonomous reference data creation
    enable_agentic_mode: bool = Field(default=True, validation_alias="ENABLE_AGENTIC_MODE")
    enable_auto_reference_data: bool = Field(default=True, validation_alias="ENABLE_AUTO_REFERENCE_DATA")
    agent_audit_retention_days: int = Field(default=90, validation_alias="AGENT_AUDIT_RETENTION_DAYS")
    require_approval_for_writes: bool = Field(default=True, validation_alias="REQUIRE_APPROVAL_FOR_WRITES")

    # Auth headers for Phase 2 API calls
    auth_token_type: str = Field(default="SESSION_TOKEN", validation_alias="AI_AUTH_TOKEN_TYPE")
    auth_header_name: str = Field(default="X-HSBC-E2E-Trust-Token", validation_alias="AI_AUTH_HEADER_NAME")
    correlation_id_header: str = Field(default="x-correlation-id", validation_alias="AI_CORRELATION_ID_HEADER")
    session_id_header: str = Field(default="x-usersession-id", validation_alias="AI_SESSION_ID_HEADER")


class APISettings(BaseSettings):
    """API Server Configuration"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    port: int = Field(default=5001, validation_alias="API_PORT")
    debug: bool = Field(default=False, validation_alias="API_DEBUG")
    reload: bool = Field(default=False, validation_alias="API_RELOAD")
    workers: int = Field(default=1, validation_alias="API_WORKERS")

    # CORS
    cors_origins: List[str] = Field(default=["*"], validation_alias="CORS_ORIGINS")

    # Rate Limiting
    rate_limit_requests: int = Field(default=100, validation_alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, validation_alias="RATE_LIMIT_WINDOW")

    # Query Settings
    default_query_timeout_ms: int = Field(default=60000, validation_alias="DEFAULT_QUERY_TIMEOUT")
    max_query_timeout_ms: int = Field(default=120000, validation_alias="MAX_QUERY_TIMEOUT")


class CacheSettings(BaseSettings):
    """Caching Configuration"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    enable_cache: bool = Field(default=True, validation_alias="ENABLE_CACHE")
    cache_ttl_seconds: int = Field(default=300, validation_alias="CACHE_TTL")
    max_cache_size: int = Field(default=1000, validation_alias="MAX_CACHE_SIZE")


class SSESettings(BaseSettings):
    """Server-Sent Events Configuration"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    heartbeat_interval_seconds: int = Field(default=15, validation_alias="SSE_HEARTBEAT_INTERVAL")
    max_connections_per_session: int = Field(default=5, validation_alias="SSE_MAX_CONNECTIONS")
    event_queue_size: int = Field(default=100, validation_alias="SSE_QUEUE_SIZE")
    connection_timeout_seconds: int = Field(default=300, validation_alias="SSE_CONNECTION_TIMEOUT")


class PathSettings(BaseSettings):
    """File Path Configuration"""
    model_config = SettingsConfigDict(extra="ignore")

    base_dir: Path = Field(default=Path(__file__).parent.parent)

    @property
    def config_dir(self) -> Path:
        return self.base_dir / "config"

    @property
    def rules_dir(self) -> Path:
        return self.base_dir / "rules"

    @property
    def dictionaries_dir(self) -> Path:
        return self.rules_dir / "dictionaries"

    @property
    def templates_dir(self) -> Path:
        return self.rules_dir / "templates"

    @property
    def generated_dir(self) -> Path:
        return self.rules_dir / "generated"

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def static_dir(self) -> Path:
        return self.base_dir / "static"

    @property
    def html_templates_dir(self) -> Path:
        return self.base_dir / "templates"


class Settings(BaseSettings):
    """Main Settings Container"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = Field(default="Compliance Engine", validation_alias="APP_NAME")
    app_version: str = Field(default="6.0.0", validation_alias="APP_VERSION")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    ai: AIServiceSettings = Field(default_factory=AIServiceSettings)
    api: APISettings = Field(default_factory=APISettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    sse: SSESettings = Field(default_factory=SSESettings)
    paths: PathSettings = Field(default_factory=PathSettings)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Convenience function for accessing settings
settings = get_settings()
