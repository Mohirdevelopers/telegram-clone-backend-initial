import pytest
from django.core.exceptions import ValidationError
from enum import Enum


class BaseEnum(Enum):
    @classmethod
    def choices(cls):
        return [(choice.value, choice.name) for choice in cls]

    @classmethod
    def values(cls):
        return [choice.value for choice in cls]


class ChannelType(BaseEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class ChannelMembershipType(BaseEnum):
    ADMIN = "admin"
    MEMBER = "member"


@pytest.mark.django_db
def test_channel_creation(user_factory):
    from channel.models import Channel

    user = user_factory()
    channel = Channel.objects.create(name="Test Channel", owner=user)

    assert channel.name == "Test Channel"
    assert channel.owner == user
    assert channel.channel_type == ChannelType.PUBLIC.value
    assert str(channel) == "Test Channel"


@pytest.mark.django_db
def test_channel_membership_creation(user_factory):
    from channel.models import Channel, ChannelMembership

    user = user_factory()
    channel_owner = user_factory()
    channel = Channel.objects.create(name="Test Channel", owner=channel_owner)

    membership = ChannelMembership.objects.create(user=user, channel=channel)

    assert membership.user == user
    assert membership.channel == channel
    assert membership.role == ChannelMembershipType.MEMBER.value

    # Test unique_together constraint
    with pytest.raises(ValidationError):
        duplicate_membership = ChannelMembership(user=user, channel=channel)
        duplicate_membership.full_clean()


@pytest.mark.django_db
def test_channel_message_creation(user_factory):
    from channel.models import Channel, ChannelMessage

    user = user_factory()
    channel_owner = user_factory()
    channel = Channel.objects.create(name="Test Channel", owner=channel_owner)

    message = ChannelMessage.objects.create(
        channel=channel, sender=user, text="Hello, world!"
    )

    assert message.channel == channel
    assert message.sender == user
    assert message.text == "Hello, world!"
    assert message.media.name is None
    assert str(message) == f"Message from {user.username} in {channel.name}"


@pytest.mark.django_db
def test_channel_message_likes(user_factory):
    from channel.models import Channel, ChannelMessage

    user1 = user_factory()
    user2 = user_factory()
    channel_owner = user_factory()

    channel = Channel.objects.create(name="Test Channel", owner=channel_owner)

    message = ChannelMessage.objects.create(
        channel=channel, sender=user1, text="Like this message!"
    )
    message.likes.add(user2)

    message.refresh_from_db()

    assert 1 == message.likes.count()


@pytest.mark.django_db
def test_channel_scheduled_message_creation(user_factory):
    from channel.models import Channel, ChannelScheduledMessage

    from datetime import datetime, timedelta

    user = user_factory()
    channel_owner = user_factory()
    channel = Channel.objects.create(name="Test Channel", owner=channel_owner)

    scheduled_time = datetime.now() + timedelta(days=1)

    scheduled_message = ChannelScheduledMessage.objects.create(
        channel=channel,
        sender=user,
        text="Scheduled message",
        scheduled_time=scheduled_time,
    )

    assert scheduled_message.channel == channel
    assert scheduled_message.sender == user
    assert scheduled_message.text == "Scheduled message"
    assert scheduled_message.scheduled_time == scheduled_time
    assert not scheduled_message.sent


@pytest.mark.django_db
def test_channel_scheduled_message_sent_flag(user_factory):
    from channel.models import Channel, ChannelScheduledMessage

    user = user_factory()
    channel_owner = user_factory()
    channel = Channel.objects.create(name="Test Channel", owner=channel_owner)

    scheduled_message = ChannelScheduledMessage.objects.create(
        channel=channel,
        sender=user,
        text="Scheduled message",
        scheduled_time="2023-12-31T23:59:59Z",
    )

    assert not scheduled_message.sent

    scheduled_message.sent = True
    scheduled_message.save()

    assert scheduled_message.sent
