from tortoise import Tortoise
from tortoise import run_async
from Discord.models import *
import asyncio


async def init():
    await Tortoise.init(
        db_url="sqlite://db.db",
        modules={"models": ["Discord.models"]}
    )
    # await Tortoise.generate_schemas(safe=True)

    # server = await Servers.create(server_id=10101)
    # await server.save()
    # channel = await Channels.create(channel_id=20202, server=server)
    # await channel.save()
    # user_message = await UserMessages(message_id=30303, channel=channel, server=server)
    # await user_message.save()
    # response_message = await ResponseMessages(message_id=40404, user_message=user_message, channel=channel, server=server)
    # await response_message.save()

    server = await Servers.get(server_id=10101)
    print(server)
    channel = await Channels.filter(channel_id=20202, server=server).first()
    user_message = await UserMessages.filter(message_id=30303, server=server, channel=channel).first()
    response = await ResponseMessages.filter(user_message=user_message, channel=channel, server=server).first()
    print(response.message_id)


if __name__ == '__main__':
    run_async(init())
