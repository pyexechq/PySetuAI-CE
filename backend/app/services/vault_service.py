"""Hashicorp Vault health checks and platform secret bootstrap."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.services.secrets_service import secrets_backend_name, vault_auth_method_name

JWT_SECRET_VAULT_PATH = "helixguard/platform/jwt_secret"

INSECURE_JWT_SECRETS = frozenset(
    {
        "change-me-in-production-use-vault",
        "change-me-in-production",
        "dev-secret-change-in-production",
        "airgap-change-me-before-production",
        "",
    }
)


@dataclass
class VaultStatusResult:
    enabled: bool
    available: bool
    authenticated: bool
    addr: str
    auth_method: str | None
    mount_path: str
    jwt_from_vault: bool
    jwt_secret_insecure: bool
    error: str | None = None


def is_insecure_jwt_secret(secret: str | None) -> bool:
    return not secret or secret.strip() in INSECURE_JWT_SECRETS


async def load_jwt_secret_from_vault() -> str | None:
    if not settings.vault_enabled:
        return None
    from app.services.secrets_service import _read_vault

    value = await _read_vault(JWT_SECRET_VAULT_PATH)
    return value if value else None


async def check_vault_status(*, jwt_from_vault: bool = False) -> VaultStatusResult:
    from app.core.security import get_jwt_secret

    active_secret = get_jwt_secret()
    if not settings.vault_enabled:
        return VaultStatusResult(
            enabled=False,
            available=False,
            authenticated=False,
            addr=settings.vault_addr,
            auth_method=None,
            mount_path=settings.vault_mount_path,
            jwt_from_vault=False,
            jwt_secret_insecure=is_insecure_jwt_secret(active_secret),
        )

    try:
        from app.services.secrets_service import _get_vault_client

        client = _get_vault_client()
        authenticated = client.is_authenticated()
        return VaultStatusResult(
            enabled=True,
            available=authenticated,
            authenticated=authenticated,
            addr=settings.vault_addr,
            auth_method=vault_auth_method_name(),
            mount_path=settings.vault_mount_path,
            jwt_from_vault=jwt_from_vault,
            jwt_secret_insecure=is_insecure_jwt_secret(active_secret),
        )
    except Exception as exc:
        return VaultStatusResult(
            enabled=True,
            available=False,
            authenticated=False,
            addr=settings.vault_addr,
            auth_method=vault_auth_method_name(),
            mount_path=settings.vault_mount_path,
            jwt_from_vault=jwt_from_vault,
            jwt_secret_insecure=is_insecure_jwt_secret(active_secret),
            error=str(exc),
        )


def assert_production_security(jwt_secret: str) -> None:
    if settings.debug:
        return
    if is_insecure_jwt_secret(jwt_secret):
        raise RuntimeError(
            "Refusing to start: JWT secret is insecure. Set JWT_SECRET_KEY, enable Vault with "
            f"{JWT_SECRET_VAULT_PATH}, or run with DEBUG=true for development."
        )
    if not settings.vault_enabled:
        print("WARNING: Vault is disabled in non-debug mode — tenant secrets stored in database.")


def vault_status_dict(result: VaultStatusResult) -> dict:
    return {
        "enabled": result.enabled,
        "available": result.available,
        "authenticated": result.authenticated,
        "addr": result.addr,
        "auth_method": result.auth_method,
        "mount_path": result.mount_path,
        "secrets_backend": secrets_backend_name(),
        "jwt_from_vault": result.jwt_from_vault,
        "jwt_secret_insecure": result.jwt_secret_insecure,
        "error": result.error,
    }
