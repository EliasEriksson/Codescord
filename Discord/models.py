from tortoise.models import Model
from tortoise import fields


class Servers(Model):
    id = fields.IntField(True)
    server_id = fields.IntField()


class Channels(Model):
    id = fields.IntField(True)
    server = fields.ForeignKeyField(f"models.{Servers.__name__}")
    channel_id = fields.IntField()


class UserMessages(Model):
    id = fields.IntField(True)
    server = fields.ForeignKeyField(f"models.{Servers.__name__}")
    channel = fields.ForeignKeyField(f"models.{Channels.__name__}")
    message_id = fields.IntField()


class ResponseMessages(Model):
    id = fields.IntField(True)
    server = fields.ForeignKeyField(f"models.{Servers.__name__}")
    channel = fields.ForeignKeyField(f"models.{Channels.__name__}")
    user_message = fields.ForeignKeyField(f"models.{UserMessages.__name__}")
    message_id = fields.IntField()
