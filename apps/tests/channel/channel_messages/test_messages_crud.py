import pytest
from rest_framework import status
from channel.models import Channel, ChannelMessage, ChannelMembership
from unittest.mock import MagicMock
from share.services import TokenService
from unittest.mock import patch


@pytest.mark.django_db
class TestChannelMessageListCreateView:
    @pytest.fixture
    def channel(self, user_factory):
        owner = user_factory.create()
        return Channel.objects.create(name="Test Channel", owner=owner)

    def test_list_messages(self, mocker, tokens, api_client, channel, user_factory):
        member = user_factory.create()
        ChannelMembership.objects.create(channel=channel, user=member)

        ChannelMessage.objects.create(
            channel=channel, sender=channel.owner, text="First Message"
        )
        ChannelMessage.objects.create(
            channel=channel, sender=member, text="Second Message"
        )

        mock_redis_client = MagicMock()
        mocker.patch.object(
            TokenService, "get_redis_client", return_value=mock_redis_client
        )

        access, _ = tokens(member)
        client = api_client(access)
        mock_redis_client.smembers.return_value = {access.encode()}

        response = client.get(f"/api/channels/{channel.id}/messages/")
        assert response.status_code == status.HTTP_200_OK
        assert (
            len(response.data["results"]) == 2
        ), "Expected two messages in the response"

    @patch("share.tasks.send_push_notification.delay")
    def test_create_message_as_owner(
        self,
        mock_send_push_notification,
        mocker,
        tokens,
        api_client,
        channel,
        user_factory,
    ):
        member = user_factory.create()
        ChannelMembership.objects.create(channel=channel, user=member)

        mock_redis_client = MagicMock()
        mocker.patch.object(
            TokenService, "get_redis_client", return_value=mock_redis_client
        )

        access, _ = tokens(channel.owner)
        client = api_client(access)
        mock_redis_client.smembers.return_value = {access.encode()}

        data = {"text": "Hello, this is a new message"}
        response = client.post(f"/api/channels/{channel.id}/messages/", data=data)

        assert response.status_code == status.HTTP_201_CREATED
        assert (
            response.data["text"] == "Hello, this is a new message"
        ), "Text content mismatch"

        if not mock_send_push_notification.called:
            print("send_push_notification.delay was not called.")

        mock_send_push_notification.assert_called_once_with(
            member.id, f"New Message in {channel.name}", "Hello, this is a new message"
        )

    def test_create_message_as_non_owner(
        self, mocker, tokens, api_client, channel, user_factory
    ):
        non_owner = user_factory.create()

        mock_redis_client = MagicMock()
        mocker.patch.object(
            TokenService, "get_redis_client", return_value=mock_redis_client
        )

        access, _ = tokens(non_owner)
        client = api_client(access)
        mock_redis_client.smembers.return_value = {access.encode()}

        data = {"text": "Hello, I shouldn't be able to post this"}
        response = client.post(f"/api/channels/{channel.id}/messages/", data=data)

        assert (
            response.status_code == status.HTTP_403_FORBIDDEN
        ), "Non-owner should not be able to create messages"


@pytest.mark.django_db
class TestChannelMessageDetailView:
    @pytest.fixture
    def channel(self, user_factory):
        owner = user_factory.create()
        return Channel.objects.create(name="Test Channel", owner=owner)

    @pytest.fixture
    def message(self, channel):
        return ChannelMessage.objects.create(
            channel=channel, sender=channel.owner, text="Test Message"
        )

    def test_read_message(self, mocker, tokens, api_client, message, user_factory):
        member = user_factory.create()
        ChannelMembership.objects.create(channel=message.channel, user=member)

        mock_redis_client = MagicMock()
        mocker.patch.object(
            TokenService, "get_redis_client", return_value=mock_redis_client
        )

        access, _ = tokens(member)
        client = api_client(access)
        mock_redis_client.smembers.return_value = {access.encode()}

        response = client.get(
            f"/api/channels/{message.channel.id}/messages/{message.id}/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["text"] == "Test Message", "Expected text content mismatch"

    def test_update_message_as_owner(self, mocker, tokens, api_client, message):
        mock_redis_client = MagicMock()
        mocker.patch.object(
            TokenService, "get_redis_client", return_value=mock_redis_client
        )

        access, _ = tokens(message.channel.owner)
        client = api_client(access)
        mock_redis_client.smembers.return_value = {access.encode()}

        data = {"text": "Updated Message"}
        response = client.patch(
            f"/api/channels/{message.channel.id}/messages/{message.id}/", data=data
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["text"] == "Updated Message", "Text should be updated"

    def test_update_message_as_non_owner(
        self, mocker, tokens, api_client, message, user_factory
    ):
        non_owner = user_factory.create()
        mock_redis_client = MagicMock()
        mocker.patch.object(
            TokenService, "get_redis_client", return_value=mock_redis_client
        )

        access, _ = tokens(non_owner)
        client = api_client(access)
        mock_redis_client.smembers.return_value = {access.encode()}

        data = {"text": "Attempted Update"}
        response = client.patch(
            f"/api/channels/{message.channel.id}/messages/{message.id}/", data=data
        )

        assert (
            response.status_code == status.HTTP_403_FORBIDDEN
        ), "Non-owner should not be able to update messages"

    def test_delete_message_as_owner(self, mocker, tokens, api_client, message):
        mock_redis_client = MagicMock()
        mocker.patch.object(
            TokenService, "get_redis_client", return_value=mock_redis_client
        )
        access, _ = tokens(message.channel.owner)

        client = api_client(access)
        mock_redis_client.smembers.return_value = {access.encode()}

        response = client.delete(
            f"/api/channels/{message.channel.id}/messages/{message.id}/"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ChannelMessage.objects.filter(
            id=message.id
        ).exists(), "Message should be deleted"

    def test_delete_message_as_non_owner(
        self, mocker, tokens, api_client, message, user_factory
    ):
        non_owner = user_factory.create()

        mock_redis_client = MagicMock()
        mocker.patch.object(
            TokenService, "get_redis_client", return_value=mock_redis_client
        )

        access, _ = tokens(non_owner)
        client = api_client(access)
        mock_redis_client.smembers.return_value = {access.encode()}

        response = client.delete(
            f"/api/channels/{message.channel.id}/messages/{message.id}/"
        )
        assert (
            response.status_code == status.HTTP_403_FORBIDDEN
        ), "Non-owner should not be able to delete messages"
