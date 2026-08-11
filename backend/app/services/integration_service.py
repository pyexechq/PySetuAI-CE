from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.governance import TenantIntegration

_LOCAL_OLLAMA_URLS = {
    "http://localhost:11434",
    "http://127.0.0.1:11434",
}


def resolve_ollama_base_url(configured: str) -> str:
    """Prefer platform Ollama URL when tenant still has a localhost default in Docker."""
    normalized = configured.rstrip("/")
    platform = settings.ollama_base_url.rstrip("/")
    if normalized in _LOCAL_OLLAMA_URLS and platform not in _LOCAL_OLLAMA_URLS:
        return settings.ollama_base_url
    return configured


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "••••••••"
    return f"{value[:4]}••••{value[-4:]}"


@dataclass
class GatewayConfig:
    openai_api_key: str | None
    gemini_api_key: str | None
    gemini_default_model: str
    ollama_enabled: bool
    ollama_base_url: str
    ollama_default_model: str
    source: str
    openai_api_base: str | None = None

    def resolve_upstream(self, model: str) -> str:
        model_l = model.lower()
        if "gemini" in model_l and self.gemini_api_key:
            return "gemini"
        if self.openai_api_key:
            return "openai"
        if self.gemini_api_key:
            return "gemini"
        if self.ollama_enabled:
            return "ollama"
        return "mock"

    @property
    def upstream(self) -> str:
        if self.openai_api_key:
            return "openai"
        if self.gemini_api_key:
            return "gemini"
        if self.ollama_enabled:
            return "ollama"
        return "mock"


async def resolve_gateway_config(db: AsyncSession, tenant_id) -> GatewayConfig:
    from app.services.secrets_service import GEMINI_SECRET, OPENAI_SECRET, get_tenant_secret, secrets_backend_name

    result = await db.execute(select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id))
    row = result.scalar_one_or_none()

    openai_key = settings.openai_api_key
    gemini_key = settings.gemini_api_key
    gemini_model = settings.gemini_default_model
    ollama_enabled = settings.ollama_enabled
    ollama_base_url = settings.ollama_base_url
    ollama_default_model = settings.ollama_default_model
    source = "environment"

    tenant_openai = await get_tenant_secret(db, tenant_id, OPENAI_SECRET)
    tenant_gemini = await get_tenant_secret(db, tenant_id, GEMINI_SECRET)

    if tenant_openai:
        openai_key = tenant_openai
        source = secrets_backend_name()
    elif row and row.openai_api_key:
        openai_key = row.openai_api_key
        source = "tenant_settings"

    if tenant_gemini:
        gemini_key = tenant_gemini
        source = secrets_backend_name() if source == "environment" else source
    elif row and row.gemini_api_key:
        gemini_key = row.gemini_api_key
        source = "tenant_settings" if source == "environment" else source

    if row:
        if row.gemini_default_model:
            gemini_model = row.gemini_default_model
        if row.ollama_enabled:
            ollama_enabled = True
            source = "tenant_settings" if source == "environment" else source
        if row.ollama_base_url:
            ollama_base_url = resolve_ollama_base_url(row.ollama_base_url)
        if row.ollama_default_model:
            ollama_default_model = row.ollama_default_model

    if settings.air_gap_mode:
        openai_key = None
        gemini_key = None
        ollama_enabled = True
        source = "air_gap"

    return GatewayConfig(
        openai_api_key=openai_key,
        gemini_api_key=gemini_key,
        gemini_default_model=gemini_model,
        ollama_enabled=ollama_enabled,
        ollama_base_url=ollama_base_url,
        ollama_default_model=ollama_default_model,
        source=source,
    )


async def get_or_create_integration(db: AsyncSession, tenant_id) -> TenantIntegration:
    result = await db.execute(select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id))
    row = result.scalar_one_or_none()
    if row is None:
        row = TenantIntegration(
            tenant_id=tenant_id,
            ollama_enabled=settings.ollama_enabled,
            ollama_base_url=settings.ollama_base_url,
            ollama_default_model=settings.ollama_default_model,
            gemini_default_model=settings.gemini_default_model,
        )
        db.add(row)
        await db.flush()
    return row
