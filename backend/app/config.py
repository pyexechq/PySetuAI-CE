from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "PySetu AI"
    app_version: str = "0.1.0"
    debug: bool = True
    demo_credentials_enabled: bool = False
    demo_seed_password: str | None = None
    demo_platform_admin_password: str | None = None
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://pysetu:pysetu@localhost:5432/pysetu"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-production-use-vault"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    cors_origins: list[str] = ["http://localhost:3000"]
    frontend_url: str = "http://localhost:3000"

    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_default_model: str = "gemini-1.5-pro"
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.2"
    gateway_mock_mode: bool = True
    air_gap_mode: bool = False

    deployment_mode: str = "saas"
    platform_portal_enabled: bool = True
    platform_tenant_slug: str = "platform"
    app_base_domain: str = "localhost"
    app_base_scheme: str = "http"

    rate_limit_enabled: bool = True
    rate_limit_auth_requests: int = 30
    rate_limit_login_requests: int = 10
    rate_limit_window_seconds: int = 60

    vault_enabled: bool = False
    vault_addr: str = "http://localhost:8200"
    vault_auth_method: str = "token"
    vault_token: str | None = None
    vault_role_id: str | None = None
    vault_secret_id: str | None = None
    vault_mount_path: str = "secret"

    llm_rebalance_schedule_enabled: bool = True
    llm_rebalance_cron_hour: int = 2
    llm_rebalance_cron_minute: int = 0

    otel_enabled: bool = True
    otel_service_name: str = "pysetu-api"
    otel_exporter: str = "console"
    otel_otlp_endpoint: str | None = None

    opa_enabled: bool = False
    opa_base_url: str = "http://localhost:8181"
    opa_policy_path: str = "pysetu/gateway/decision"
    opa_timeout_seconds: float = 2.0
    opa_fail_open: bool = True

    oidc_enabled: bool = True
    oidc_state_redis_prefix: str = "oidc:state:"
    oidc_jit_provision_default: bool = False
    oidc_default_role: str = "developer"

    smtp_enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "pysetu@localhost"
    smtp_use_tls: bool = False

    @property
    def gateway_upstream(self) -> str:
        if self.openai_api_key:
            return "openai"
        if self.ollama_enabled:
            return "ollama"
        return "mock"

    @property
    def platform_portal_active(self) -> bool:
        return self.platform_portal_enabled

    @property
    def is_saas_deployment(self) -> bool:
        return self.deployment_mode.strip().lower() == "saas"


settings = Settings()
