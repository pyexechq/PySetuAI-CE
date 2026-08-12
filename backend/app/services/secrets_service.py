"""Tenant and provider secret storage with optional Hashicorp Vault backend."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.governance import LLMProvider, TenantIntegration
from app.services.integration_service import mask_secret

OPENAI_SECRET = "openai_api_key"
GEMINI_SECRET = "gemini_api_key"
AI_ASSIST_SECRET = "ai_assist_api_key"

_vault_token_cache: dict[str, float | str | None] = {
    "token": None,
    "expires_at": 0.0,
}


def _tenant_secret_path(tenant_id: uuid.UUID, secret_name: str) -> str:
    return f"pysetu/tenants/{tenant_id}/integrations/{secret_name}"


def _provider_secret_path(tenant_id: uuid.UUID, provider_id: uuid.UUID) -> str:
    return f"pysetu/tenants/{tenant_id}/providers/{provider_id}/api_key"


def _mcp_oauth_secret_path(tenant_id: uuid.UUID, server_id: uuid.UUID, secret_name: str) -> str:
    return f"pysetu/tenants/{tenant_id}/mcp/{server_id}/oauth/{secret_name}"


def _user_mcp_secret_path(tenant_id: uuid.UUID, user_id: uuid.UUID, server_id: uuid.UUID) -> str:
    return f"pysetu/tenants/{tenant_id}/users/{user_id}/mcp/{server_id}/access_token"


def _validate_vault_settings() -> None:
    method = (settings.vault_auth_method or "token").strip().lower()
    if method not in {"token", "approle"}:
        raise RuntimeError(f"Unsupported VAULT_AUTH_METHOD: {settings.vault_auth_method}")
    if method == "token" and not settings.vault_token:
        raise RuntimeError("Vault token auth requires VAULT_TOKEN")
    if method == "approle" and (not settings.vault_role_id or not settings.vault_secret_id):
        raise RuntimeError("Vault AppRole auth requires VAULT_ROLE_ID and VAULT_SECRET_ID")


def _login_vault_approle(client) -> str:
    response = client.auth.approle.login(
        role_id=settings.vault_role_id,
        secret_id=settings.vault_secret_id,
    )
    auth = response.get("auth") if isinstance(response, dict) else None
    if not isinstance(auth, dict) or not auth.get("client_token"):
        raise RuntimeError("Vault AppRole login did not return a client token")
    lease_duration = auth.get("lease_duration")
    if isinstance(lease_duration, (int, float)) and lease_duration > 0:
        _vault_token_cache["expires_at"] = time.time() + float(lease_duration)
    else:
        _vault_token_cache["expires_at"] = time.time() + 3600
    token = str(auth["client_token"])
    _vault_token_cache["token"] = token
    return token


def _get_vault_client():
    try:
        import hvac
    except ImportError as exc:
        raise RuntimeError("Vault is enabled but hvac is not installed") from exc

    _validate_vault_settings()
    method = settings.vault_auth_method.strip().lower()
    client = hvac.Client(url=settings.vault_addr)

    if method == "approle":
        cached_token = _vault_token_cache.get("token")
        expires_at = float(_vault_token_cache.get("expires_at") or 0)
        if isinstance(cached_token, str) and cached_token and time.time() < expires_at - 60:
            client.token = cached_token
            if client.is_authenticated():
                return client
        client.token = _login_vault_approle(client)
    else:
        client.token = settings.vault_token

    if not client.is_authenticated():
        raise RuntimeError("Vault authentication failed")
    return client


def _vault_read(path: str) -> str | None:
    client = _get_vault_client()
    mount = settings.vault_mount_path.strip("/")
    try:
        response = client.secrets.kv.v2.read_secret_version(
            path=path, mount_point=mount, raise_on_deleted_version=False
        )
    except Exception as exc:
        if type(exc).__name__ == "InvalidPath" or "not found" in str(exc).lower():
            return None
        raise
    data = response.get("data", {}).get("data", {})
    value = data.get("value")
    return value if isinstance(value, str) and value else None


def _vault_write(path: str, value: str | None) -> None:
    client = _get_vault_client()
    mount = settings.vault_mount_path.strip("/")
    if value:
        client.secrets.kv.v2.create_or_update_secret(path=path, secret={"value": value}, mount_point=mount)
    else:
        try:
            client.secrets.kv.v2.delete_metadata_and_all_versions(path=path, mount_point=mount)
        except Exception:
            pass


async def _read_vault(path: str) -> str | None:
    return await asyncio.to_thread(_vault_read, path)


async def _write_vault(path: str, value: str | None) -> None:
    await asyncio.to_thread(_vault_write, path, value)


async def _get_integration_row(db: AsyncSession, tenant_id: uuid.UUID) -> TenantIntegration | None:
    result = await db.execute(select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id))
    return result.scalar_one_or_none()


async def get_tenant_secret(db: AsyncSession, tenant_id: uuid.UUID, secret_name: str) -> str | None:
    if settings.vault_enabled:
        value = await _read_vault(_tenant_secret_path(tenant_id, secret_name))
        if value is not None:
            return value

    row = await _get_integration_row(db, tenant_id)
    if row is None:
        return None
    return getattr(row, secret_name, None)


async def set_tenant_secret(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    secret_name: str,
    value: str | None,
) -> None:
    row = await _get_integration_row(db, tenant_id)
    if row is None:
        from app.services.integration_service import get_or_create_integration

        row = await get_or_create_integration(db, tenant_id)

    if settings.vault_enabled:
        await _write_vault(_tenant_secret_path(tenant_id, secret_name), value)
        setattr(row, secret_name, None)
        return

    setattr(row, secret_name, value)


async def get_provider_secret(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    provider: LLMProvider,
) -> str | None:
    if settings.vault_enabled:
        value = await _read_vault(_provider_secret_path(tenant_id, provider.id))
        if value is not None:
            return value
    return provider.api_key


async def set_provider_secret(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    provider: LLMProvider,
    value: str | None,
) -> None:
    if settings.vault_enabled:
        await _write_vault(_provider_secret_path(tenant_id, provider.id), value)
        provider.api_key = None
        return
    provider.api_key = value


async def get_mcp_oauth_secret(
    tenant_id: uuid.UUID,
    server_id: uuid.UUID,
    secret_name: str,
    db_value: str | None,
) -> str | None:
    if settings.vault_enabled:
        value = await _read_vault(_mcp_oauth_secret_path(tenant_id, server_id, secret_name))
        if value is not None:
            return value
    return db_value


async def set_mcp_oauth_secret(
    tenant_id: uuid.UUID,
    server_id: uuid.UUID,
    secret_name: str,
    value: str | None,
) -> str | None:
    if settings.vault_enabled:
        await _write_vault(_mcp_oauth_secret_path(tenant_id, server_id, secret_name), value)
        return None
    return value


async def get_user_mcp_secret(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    server_id: uuid.UUID,
    db_value: str | None,
) -> str | None:
    if settings.vault_enabled:
        value = await _read_vault(_user_mcp_secret_path(tenant_id, user_id, server_id))
        if value is not None:
            return value
    return db_value


async def set_user_mcp_secret(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    server_id: uuid.UUID,
    value: str | None,
) -> str | None:
    if settings.vault_enabled:
        await _write_vault(_user_mcp_secret_path(tenant_id, user_id, server_id), value)
        return None
    return value


async def provider_secret_status(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    provider: LLMProvider,
) -> tuple[bool, str | None]:
    secret = await get_provider_secret(db, tenant_id, provider)
    return bool(secret), mask_secret(secret)


async def apply_provider_gateway_credentials(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    routed_model: str,
    config,
):
    result = await db.execute(
        select(LLMProvider).where(
            LLMProvider.tenant_id == tenant_id,
            LLMProvider.is_active.is_(True),
            LLMProvider.name.ilike(routed_model.strip()),
        )
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        return config

    api_key = await get_provider_secret(db, tenant_id, provider)
    if not api_key:
        return config

    provider_type = provider.provider_type.lower()
    if provider_type == "custom":
        return replace(
            config,
            openai_api_key=api_key,
            openai_api_base=provider.endpoint_url,
            source="provider_registry",
        )
    if provider_type in {"openai", "azure", "anthropic"}:
        return replace(config, openai_api_key=api_key, source="provider_registry")
    if provider_type == "gemini":
        return replace(config, gemini_api_key=api_key, source="provider_registry")
    if provider_type == "ollama":
        return replace(config, ollama_enabled=True, source="provider_registry")
    return config


def secrets_backend_name() -> str:
    return "vault" if settings.vault_enabled else "database"


def vault_auth_method_name() -> str | None:
    if not settings.vault_enabled:
        return None
    return settings.vault_auth_method.strip().lower()
