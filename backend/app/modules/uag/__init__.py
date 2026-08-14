"""Universal AI Gateway — protocol translation and provider compatibility."""

from app.modules.uag.canonical import CanonicalPrompt, TranslationTrace

__all__ = [
    "CanonicalPrompt",
    "TranslationTrace",
    "run_uag_pre_governance",
    "run_uag_post_upstream",
    "simulate_translation",
]


def __getattr__(name: str):
    if name in {"run_uag_pre_governance", "run_uag_post_upstream", "simulate_translation"}:
        from app.modules.uag import service

        return getattr(service, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
