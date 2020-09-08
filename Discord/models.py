from typing import *
from tortoise.models import Model
from tortoise import fields
import tortoise


class Servers(Model):
    id = fields.IntField(pk=True)
    server_id = fields.IntField()
    auto_run = fields.BooleanField(default=False)

    @classmethod
    async def create_server(cls, server_id: int, auto_run: bool = None) -> Model:
        try:
            server = await cls.get(
                server_id=server_id
            )
        except tortoise.exceptions.DoesNotExist:
            server = await cls.create(
                server_id=server_id,
                auto_run=True if auto_run else False
            )
        return server


class Channels(Model):
    id = fields.IntField(pk=True)
    server = fields.ForeignKeyField(f"models.{Servers.__name__}")
    channel_id = fields.IntField()


class UserMessages(Model):
    id = fields.IntField(pk=True)
    server = fields.ForeignKeyField(f"models.{Servers.__name__}")
    channel = fields.ForeignKeyField(f"models.{Channels.__name__}")
    message_id = fields.IntField()


class ResponseMessages(Model):
    id = fields.IntField(pk=True)
    server = fields.ForeignKeyField(f"models.{Servers.__name__}")
    channel = fields.ForeignKeyField(f"models.{Channels.__name__}")
    user_message = fields.ForeignKeyField(f"models.{UserMessages.__name__}")
    message_id = fields.IntField()

    @classmethod
    async def create_message(
            cls, server_id: int, channel_id: int,
            user_message_id: int, message_id: int) -> "ResponseMessages":
        try:
            server = await Servers.get(
                server_id=server_id)
        except tortoise.exceptions.DoesNotExist:
            server = await Servers.create(
                server_id=server_id)
            await server.save()

        try:
            channel = await Channels.get(
                server=server,
                channel_id=channel_id)
        except tortoise.exceptions.DoesNotExist:
            channel = await Channels.create(
                server=server,
                channel_id=channel_id)

        try:
            user_message = await UserMessages.get(
                server=server,
                channel=channel,
                message_id=user_message_id)
        except tortoise.exceptions.DoesNotExist:
            user_message = await UserMessages.create(
                server=server,
                channel=channel,
                message_id=user_message_id)

        response_message = await cls.create(
            server=server,
            channel=channel,
            user_message=user_message,
            message_id=message_id)
        return response_message

    @classmethod
    async def get_message(
            cls, server_id: int, channel_id: int,
            user_message_id: int) -> "ResponseMessages":
        server = await Servers.get(
            server_id=server_id)
        if not server:
            server = await Servers.create(
                server_id=server_id)
            await server.save()

        channel = await Channels.get(
            server=server,
            channel_id=channel_id)
        if not channel:
            channel = Channels.create(
                server=server,
                channel_id=channel_id)

        user_message = await UserMessages.get(
            server=server,
            channel=channel,
            message_id=user_message_id)
        if not user_message:
            user_message = await UserMessages.create(
                server=server,
                channel=channel,
                message_id=user_message_id)

        response_message = await cls.get(server=server, channel=channel, user_message=user_message)
        return response_message
