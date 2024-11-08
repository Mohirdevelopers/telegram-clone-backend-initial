import pytest
import uuid
from rest_framework import status
from unittest.mock import patch
from unittest.mock import MagicMock
from share.services import TokenService
from core import settings

LOGOUT_URL = "/api/users/logout/"


@pytest.mark.django_db
@patch.object(TokenService, "add_token_to_redis")
def test_logout(mock_add_token, api_client, user_factory, mocker, tokens):
    user = user_factory.create()

    mock_redis_client = MagicMock()
    mocker.patch.object(
        TokenService, "get_redis_client", return_value=mock_redis_client
    )

    access, _ = tokens(user)
    client = api_client(access)

    mock_redis_client.smembers.return_value = {access.encode()}

    response = client.post(LOGOUT_URL)

    # Assertions
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"detail": "Successfully logged out"}
    assert mock_add_token.call_count == 2

    mock_add_token.assert_any_call(
        uuid.UUID(str(user.id)),
        "fake_token",
        "access",
        settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"],
    )
    mock_add_token.assert_any_call(
        uuid.UUID(str(user.id)),
        "fake_token",
        "refresh",
        settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"],
    )


@pytest.mark.django_db
def test_logout_unauthenticated(api_client):
    response = api_client().post(LOGOUT_URL)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
