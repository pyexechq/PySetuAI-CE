from app.services.regional_routing_service import resolve_provider_region


def test_resolve_provider_region_maps_data_residency_bundles() -> None:
    assert resolve_provider_region("bedrock", "India residency") == "ap-south-1"
    assert resolve_provider_region("vertex", "EU strict") == "europe-west3"
    assert resolve_provider_region("bedrock", "US standard") == "us-east-1"


def test_resolve_provider_region_defaults_to_us() -> None:
    assert resolve_provider_region("vertex", None) == "us-central1"
    assert resolve_provider_region("unknown", "EU") == "europe-west3"