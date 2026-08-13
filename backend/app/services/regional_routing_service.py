from __future__ import annotations

BEDROCK_REGIONS = {"US": "us-east-1", "EU": "eu-central-1", "INDIA": "ap-south-1"}
VERTEX_REGIONS = {"US": "us-central1", "EU": "europe-west3", "INDIA": "asia-south1"}


def resolve_provider_region(provider: str, policy_bundle_name: str | None = None) -> str:
    """Resolve a provider-native region from the active routing/data-residency bundle."""
    bundle = (policy_bundle_name or "").upper()
    requested = "INDIA" if "INDIA" in bundle else "EU" if "EU" in bundle else "US"
    regions = BEDROCK_REGIONS if provider.lower() == "bedrock" else VERTEX_REGIONS
    return regions.get(requested, next(iter(regions.values())))