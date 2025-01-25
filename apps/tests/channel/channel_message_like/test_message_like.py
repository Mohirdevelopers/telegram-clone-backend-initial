import pytest
from rest_framework import status
from unittest.mock import MagicMock
from share.services import TokenService
from django.contrib.auth import get_user_model
from channel.models import Channel, ChannelMessage

User = get_user_model()


@pytest.fixture
def setup_data(user_factory):
    user = user_factory.create()
    channel = Channel.objects.create(name="Test Channel", owner=user)
    message = ChannelMessage.objects.create(
        channel=channel, sender=user, text="Hello, World!"
    )
    return {"user": user, "channel": channel, "message": message}


@pytest.mark.django_db
class TestLikeMessageView:
    def test_like_message(self, api_client, tokens, mocker, setup_data):
        mock_redis_client = MagicMock()
        mocker.patch.object(
            TokenService, "get_redis_client", return_value=mock_redis_client
        )

        access, _ = tokens(setup_data["user"])
        client = api_client(access)

        mock_redis_client.smembers.return_value = {access.encode()}

        response = client.post(
            f"/api/channels/{setup_data['channel'].id}/messages/{setup_data['message'].id}/like/"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Message liked."
        assert setup_data["message"].likes.filter(id=setup_data["user"].id).exists()

    def test_unlike_message(self, api_client, tokens, mocker, setup_data):
        mock_redis_client = MagicMock()
        mocker.patch.object(
            TokenService, "get_redis_client", return_value=mock_redis_client
        )

        access, _ = tokens(setup_data["user"])
        client = api_client(access)

        mock_redis_client.smembers.return_value = {access.encode()}

        setup_data["message"].likes.add(setup_data["user"])

        response = client.delete(
            f"/api/channels/{setup_data['channel'].id}/messages/{setup_data['message'].id}/like/"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Like removed."
        assert not setup_data["message"].likes.filter(id=setup_data["user"].id).exists()

    def test_like_message_unauthenticated(self, api_client, setup_data):
        client = api_client()
        response = client.post(
            f"/api/channels/{setup_data['channel'].id}/messages/{setup_data['message'].id}/like/"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
