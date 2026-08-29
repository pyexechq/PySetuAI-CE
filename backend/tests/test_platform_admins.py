import pytest
from app.schemas.auth import ChangePasswordRequest, ChangePasswordResponse
from app.schemas.platform import (
    PlatformAdminCreateRequest,
    PlatformAdminResponse,
    PlatformAdminUpdateRequest,
)


def test_change_password_schema_validation():
    req = ChangePasswordRequest(
        current_password="oldpassword123",
        new_password="newpassword456",
    )
    assert req.current_password == "oldpassword123"
    assert req.new_password == "newpassword456"

    # Must fail if new_password < 8 chars
    with pytest.raises(Exception):
        ChangePasswordRequest(
            current_password="oldpassword123",
            new_password="short",
        )


def test_platform_admin_schemas():
    create_req = PlatformAdminCreateRequest(
        email="ops@pysetu.com",
        name="Ops Admin",
        password="supersecretpassword123",
    )
    assert create_req.email == "ops@pysetu.com"
    assert create_req.name == "Ops Admin"
    assert create_req.password == "supersecretpassword123"

    update_req = PlatformAdminUpdateRequest(
        name="Updated Name",
        is_active=False,
        new_password="anotherpassword999",
    )
    assert update_req.name == "Updated Name"
    assert update_req.is_active is False
    assert update_req.new_password == "anotherpassword999"

    resp = PlatformAdminResponse(
        id="11111111-1111-1111-1111-111111111111",
        email="ops@pysetu.com",
        name="Ops Admin",
        role="platform_admin",
        is_active=True,
    )
    assert resp.email == "ops@pysetu.com"
    assert resp.role == "platform_admin"
