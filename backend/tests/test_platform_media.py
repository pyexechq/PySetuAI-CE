import pytest
from app.schemas.platform import PlatformMediaItemResponse, PlatformMediaUploadResponse


def test_platform_media_schemas():
    item = PlatformMediaItemResponse(
        filename="architecture_diagram_20260825_120000_abc123.png",
        url="/api/v1/platform/media/architecture_diagram_20260825_120000_abc123.png",
        size_bytes=102400,
        mime_type="image/png",
        created_at="2026-08-25T12:00:00Z",
    )
    assert item.filename.endswith(".png")
    assert item.size_bytes == 102400
    assert item.mime_type == "image/png"

    upload_resp = PlatformMediaUploadResponse(
        url="/api/v1/platform/media/diagram.png",
        filename="diagram.png",
        size_bytes=45000,
        mime_type="image/png",
    )
    assert upload_resp.url.startswith("/api/v1/platform/media/")
    assert upload_resp.size_bytes == 45000
