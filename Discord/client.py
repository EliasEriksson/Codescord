import discord
import Codescord
import re
from .models import ResponseMessages
import asyncio


async def edit(stdout: str, message: discord.Message, description: str = None) -> None:
    description = description if description else ""
    await message.edit(content=f"{description}\n```{stdout}```")


async def send(stdout: str, channel: discord.TextChannel, description: str = None) -> discord.Message:
    description = description if description else ""
    return await channel.send(f"{description}\n```{stdout}```")


class Client(discord.Client):
    def __init__(self, loop=None) -> None:
        loop = loop if not loop else asyncio.get_event_loop()
        super(Client, self).__init__(loop=loop)
        self.codescord_client = Codescord.Client(self.loop)
        self.code_pattern = re.compile(r"```(\w+)\n([^=`]+)```", re.DOTALL)

    async def process(self, message: discord.Message) -> str:
        if message.author != self.user:
            if match := self.code_pattern.search(message.content):
                source = Codescord.Source(*match.groups())
                stdout = await self.codescord_client.process(source)
                return stdout

    async def on_message_edit(self, _, user_edited_message: discord.Message) -> None:
        if stdout := (await self.process(user_edited_message)):
            db_response_message = await ResponseMessages.get_message(
                server_id=user_edited_message.guild.id,
                channel_id=user_edited_message.channel.id,
                user_message_id=user_edited_message.id)

            response_message: discord.Message = await user_edited_message.channel.fetch_message(
                db_response_message.message_id)
            await edit(stdout, response_message)

    async def on_message(self, message: discord.Message) -> None:
        if stdout := (await self.process(message)):
            response = await send(stdout, message.channel)
            response_message = await ResponseMessages.create_message(
                server_id=message.guild.id,
                channel_id=message.channel.id,
                user_message_id=message.id,
                message_id=response.id)
            await response_message.save()

    @staticmethod
    async def on_ready():
        print("online.")
